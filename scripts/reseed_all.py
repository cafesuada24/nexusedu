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
from src.domain.services.anomaly_engine import AnomalyEngine


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
    advisors = [Advisor(**row) for row in adv_df.to_dict(orient='records')]

    # Load Students
    print('Importing students...')
    stu_df = pd.read_csv('data/v2_students.csv')
    students = [Student(**row) for row in stu_df.to_dict(orient='records')]

    # Load Activities
    print('Importing activities...')
    act_df = pd.read_csv('data/v2_activities.csv')
    activities = [Activity(**row) for row in act_df.to_dict(orient='records')]

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
        student_repo = SqlAlchemyStudentRepository(session)
        activity_repo = SqlAlchemyActivityRepository(session)
        history_repo = SqlAlchemyStatusHistoryRepository(session)

        anomaly_engine = AnomalyEngine(student_repo, activity_repo, history_repo)
        new_sids = await anomaly_engine.run()
        print(f"Anomaly detection complete. {len(new_sids)} students identified as 'new' at-risk.")

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
                        id=str(uuid.uuid4()),
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
