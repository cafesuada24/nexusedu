import asyncio
import os
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.infrastructure.database.models import (
    Activity,
    Advisor,
    AdvisorPointsLedger,
    Base,
    Student,
    User,
)
from src.infrastructure.database.session import async_session_maker, engine
from src.infrastructure.repositories.sqlalchemy_repositories import (
    SqlAlchemyActivityRepository,
    SqlAlchemyStatusHistoryRepository,
    SqlAlchemyStudentRepository,
)


from src.presentation.api.auth import SQLAlchemyUserDatabase, UserManager, UserRole
from src.presentation.schemas.auth import UserCreate


async def reseed() -> None:
    """Drops all tables, recreates schema, and seeds data from CSV files."""
    print('Stopping API (if running)...')
    os.system('pkill -f uvicorn')

    print('Initializing new database schema...')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Load Advisors
    print('Importing advisors...')
    adv_df = pd.read_csv('data/v2_advisors.csv')
    advisors = [
        Advisor(**{**row, 'advisor_id': uuid.UUID(row['advisor_id'])})
        for row in adv_df.to_dict(orient='records')
    ]

    # Load Students
    print('Importing students...')
    stu_df = pd.read_csv('data/v2_students.csv')
    students = [
        Student(**{**row, 'sid': uuid.UUID(row['sid'])})
        for row in stu_df.to_dict(orient='records')
    ]

    # Load Activities
    print('Importing activities...')
    act_df = pd.read_csv('data/v2_activities.csv')
    activities = [
        Activity(
            **{
                **row,
                'activity_id': uuid.UUID(row['activity_id']),
                'sid': uuid.UUID(row['sid']),
            }
        )
        for row in act_df.to_dict(orient='records')
    ]

    async with async_session_maker() as session:
        session.add_all(advisors)
        session.add_all(students)
        session.add_all(activities)
        
        # Create default admin user
        print('Creating default admin user (admin@example.com / password123)...')
        user_db = SQLAlchemyUserDatabase(session, User)
        user_manager = UserManager(user_db)
        user = await user_manager.create(
            UserCreate(email='admin@example.com', password='password123'),
            safe=True
        )
        # Update role to admin
        from sqlalchemy import update
        await session.execute(
            update(User).where(User.id == user.id).values(role=UserRole.ADMIN.value)
        )

        await session.commit()

        print('Running anomaly detection...')
        from collections import defaultdict
        from src.domain.services.anomaly_engine.zscore import ZScore
        from src.domain.value_objects.status import InterventionStatus, RiskStatus

        student_repo = SqlAlchemyStudentRepository(session)
        activity_repo = SqlAlchemyActivityRepository(session)
        history_repo = SqlAlchemyStatusHistoryRepository(session)

        # 1. Fetch data
        weekly_avgs = await activity_repo.get_weekly_averages()
        existing_history = await history_repo.get_all_history()

        # 2. Prepare data for the pure domain service
        history_set = {
            (h['sid'], h['academic_year'], h['semester'], h['week'])
            for h in existing_history
        }

        student_data = defaultdict(list)
        for avg in weekly_avgs:
            student_data[avg['sid']].append(avg)

        # 3. Call the pure domain service
        anomaly_engine = ZScore()
        new_history_records, risk_statuses = anomaly_engine.run(
            student_data, history_set
        )

        # 4. Persist new history records
        if new_history_records:
            await history_repo.batch_create_history(new_history_records)

        # 5. Transition student statuses and identify new at-risk students
        new_at_risk_sids = []
        for sid, latest_risk in risk_statuses.items():
            if latest_risk == RiskStatus.NORMAL:
                continue

            student = await student_repo.get_by_id(sid)
            if not student:
                continue

            if student.intervention_status in (
                InterventionStatus.NONE,
                InterventionStatus.RESOLVED,
            ):
                await student_repo.update_risk_status(
                    sid,
                    risk_status=latest_risk,
                    intervention_status=InterventionStatus.NOTIFIED,
                )
                new_at_risk_sids.append(sid)
            else:
                await student_repo.update_risk_status(sid, risk_status=latest_risk)

        print(f"Anomaly detection complete. {len(new_at_risk_sids)} students identified as 'new' at-risk.")

        print('Seeding advisor points ledger...')
        actions = [
            ('email_sent', 10),
            ('student_resolved', 50),
            ('meeting_booked', 30),
            ('draft_reviewed', 5),
        ]

        ledger_entries = []
        for adv in advisors:
            aid = adv.advisor_id
            for _ in range(random.randint(5, 15)):
                student = random.choice(students)
                action, points = random.choice(actions)
                ts = datetime.now() - timedelta(days=random.randint(0, 14))
                ledger_entries.append(
                    AdvisorPointsLedger(
                        id=uuid.uuid4(),
                        advisor_id=aid,
                        action_type=action,
                        points=points,
                        sid=student.sid,
                        timestamp=ts,
                    )
                )

        session.add_all(ledger_entries)
        await session.commit()

    print('Reseed complete.')


if __name__ == '__main__':
    asyncio.run(reseed())
