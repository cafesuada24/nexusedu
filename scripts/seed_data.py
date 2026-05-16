import asyncio
import os
import random
import sys
import uuid
import logging
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

import pandas as pd
from dateutil import parser

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.identifiers import generate_uuid
from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
    SqlAlchemyActivityRepository,
    SqlAlchemyAdvisorRepository,
    SqlAlchemyStatusHistoryRepository,
    SqlAlchemyStudentRepository,
    SqlAlchemyUserSettingsRepository,
)

from src.infrastructure.database.models import (
    Activity,
    Advisor,
    AdvisorWorkingHours,
    Base,
    Case,
    PointLedger,
    Student,
    User,
)
from src.infrastructure.database.session import async_session_maker, engine
from src.presentation.api.auth import SQLAlchemyUserDatabase, UserManager, UserRole
from src.presentation.schemas.auth import UserCreate

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def seed_data() -> None:
    """Seeds data from CSV files into the existing database schema."""
    
    # Load Advisors
    logger.info('Importing advisors...')
    adv_df = pd.read_csv('data/v2_advisors.csv')
    advisors = [
        Advisor(**{**row, 'advisor_id': uuid.UUID(row['advisor_id'])})
        for row in adv_df.to_dict(orient='records')
    ]

    # Load Students
    logger.info('Importing students...')
    stu_df = pd.read_csv('data/v2_students.csv')
    students = [
        Student(
            **{
                **row,
                'sid': uuid.UUID(row['sid']),
                'last_notified_timestamp': (
                    parser.parse(row['last_notified_timestamp'])
                    if isinstance(row.get('last_notified_timestamp'), str)
                    else None
                ),
            },
        )
        for row in stu_df.to_dict(orient='records')
    ]

    # Load Activities
    logger.info('Importing activities...')
    act_df = pd.read_csv('data/v2_activities.csv')
    activities = [
        Activity(
            **{
                **row,
                'activity_id': uuid.UUID(row['activity_id']),
                'sid': uuid.UUID(row['sid']),
                'timestamp': parser.parse(row['timestamp']),
            },
        )
        for row in act_df.to_dict(orient='records')
    ]

    async with async_session_maker() as session:
        session.add_all(advisors)
        session.add_all(students)
        session.add_all(activities)

        # Seed default working hours for all advisors
        logger.info('Seeding default working hours (Mon-Fri, 9:00-11:00 and 14:00-17:00 UTC+7)...')
        for advisor in advisors:
            for day in range(5):
                # Morning session
                session.add(
                    AdvisorWorkingHours(
                        id=generate_uuid(),
                        advisor_id=advisor.advisor_id,
                        day_of_week=day,
                        start_time=time(9, 0),
                        end_time=time(11, 0),
                        timezone='Asia/Ho_Chi_Minh',
                    ),
                )
                # Afternoon session
                session.add(
                    AdvisorWorkingHours(
                        id=generate_uuid(),
                        advisor_id=advisor.advisor_id,
                        day_of_week=day,
                        start_time=time(14, 0),
                        end_time=time(17, 0),
                        timezone='Asia/Ho_Chi_Minh',
                    ),
                )

        # Create default admin user
        logger.info('Creating default admin user (dev@gmail.com / dev)...')
        user_db = SQLAlchemyUserDatabase(session, User)
        user_settings_repo = SqlAlchemyUserSettingsRepository(session)
        from src.infrastructure.persistence.sqlalchemy_uow import SqlAlchemyUnitOfWork
        uow = SqlAlchemyUnitOfWork(session)
        user_manager = UserManager(user_db, user_settings_repo, uow)
        
        # Check if users already exist to avoid duplicates
        from sqlalchemy import select
        existing_user = await session.execute(select(User).where(User.email == 'dev@gmail.com'))
        if not existing_user.scalar_one_or_none():
            user = await user_manager.create(
                UserCreate(email='dev@gmail.com', password='dev'), safe=True,
            )
            adv = await user_manager.create(
                UserCreate(email='adv@gmail.com', password='adv'), safe=True,
            )
            # Update role to admin
            from sqlalchemy import update

            await session.execute(
                update(User).where(User.id == user.id).values(role=UserRole.ADMIN.value),
            )
            await session.execute(
                update(User).where(User.id == adv.id).values(role=UserRole.ADVISOR.value),
            )

        await session.commit()

        logger.info('Running anomaly detection...')
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
            student_data, history_set,
        )

        # 4. Persist new history records
        if new_history_records:
            await history_repo.batch_create_history(new_history_records)

        # DEBUG: Print risk statuses for non-Normal students
        print("\n--- NON-NORMAL RISK STATUSES ---")
        student_names_map = {s.sid: s.student_name for s in students}
        for sid, status in risk_statuses.items():
            if status != RiskStatus.NORMAL:
                name = student_names_map.get(sid, "Unknown")
                print(f"{name}: {status}")
        print("---------------------------\n")

        # 5. Transition student statuses and identify new at-risk students
        new_at_risk_sids = []
        for sid, latest_risk in risk_statuses.items():
            if latest_risk == RiskStatus.NORMAL:
                continue

            student = await student_repo.get_by_id(sid)
            if not student:
                continue

            student.current_risk_status = latest_risk
            await student_repo.save(student)
            new_at_risk_sids.append(sid)

        logger.info(
            f"Anomaly detection complete. {len(new_at_risk_sids)} students identified as 'new' at-risk.",
        )

        logger.info('Seeding cases and tasks...')
        # Create cases for at-risk students
        from src.domain.value_objects.status import InterventionStatus, TaskStatus

        cases = []
        for sid in new_at_risk_sids:
            case_id = generate_uuid()
            advisor = random.choice(advisors)
            cases.append(
                Case(
                    case_id=case_id,
                    sid=sid,
                    intervention_status=InterventionStatus.ACCEPTED,
                    assigned_advisor_id=advisor.advisor_id,
                    assigned_at=datetime.now(UTC),
                ),
            )

        if cases:
            session.add_all(cases)
            await session.flush()

            logger.info('Seeding point ledger...')
            ledger_entries = []
            for _ in range(20):
                case_obj = random.choice(cases)
                aid = case_obj.assigned_advisor_id
                
                ledger_entries.append(
                    PointLedger(
                        id=generate_uuid(),
                        advisor_id=aid,
                        case_id=case_obj.case_id,
                        action='system_seeded_intervention',
                        points=random.randint(5, 50),
                        earned_at=datetime.now(UTC) - timedelta(days=random.randint(0, 7)),
                    ),
                )

            session.add_all(ledger_entries)
        else:
            logger.info('No cases to seed.')
        await session.commit()

    logger.info('Data seeding complete.')


if __name__ == '__main__':
    asyncio.run(seed_data())
