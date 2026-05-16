import argparse
import asyncio
import os
import uuid
import logging
from datetime import time
from pathlib import Path
import pandas as pd
from dateutil import parser

# Add project root to sys.path
project_root = Path(__file__).parent.parent
import sys

sys.path.append(str(project_root))

from scripts.utils import require_dev_only
from src.core.identifiers import generate_uuid
from src.infrastructure.database.models import (
    Activity,
    Advisor,
    AdvisorWorkingHours,
    Base,
    Case,
    User,
    PointLedger,
    Student,
    InterventionEmail,
    Appointment,
    StudentStatusHistory,
)
from src.infrastructure.database.session import async_session_maker, engine
from src.presentation.api.auth import SQLAlchemyUserDatabase, UserManager, UserRole
from src.presentation.schemas.auth import UserCreate
from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
    SqlAlchemyUserSettingsRepository,
)
from src.infrastructure.persistence.sqlalchemy_uow import SqlAlchemyUnitOfWork

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@require_dev_only
async def reseed_dashboard(reset: bool = False) -> None:
    """Seeds data from dashboard mock CSV files. Optionally drops and recreates tables."""
    if reset:
        logger.info('Resetting database schema...')
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        user_db = SQLAlchemyUserDatabase(session, User)
        user_settings_repo = SqlAlchemyUserSettingsRepository(session)
        uow = SqlAlchemyUnitOfWork(session)
        user_manager = UserManager(user_db, user_settings_repo, uow)

        logger.info('Importing advisors and creating users...')
        adv_df = pd.read_csv('data/v2_advisors.csv')
        advisors = []
        for _, row in adv_df.iterrows():
            user_id = uuid.UUID(row['user_id'])
            try:
                # To ensure the ID matches what's in the CSV, we'll use a direct manual insert
                logger.info(f'Creating user for {row["email"]} with ID {user_id}...')

                # Check if user exists
                from sqlalchemy import select

                res = await session.execute(
                    select(User).where(User.email == row['email'])
                )
                if res.scalar_one_or_none():
                    logger.info(f'User {row["email"]} already exists, skipping creation.')
                else:
                    # Manually insert with fixed ID and hashed password
                    hashed_password = user_manager.password_helper.hash('password')
                    new_user = User(
                        id=user_id,
                        email=row['email'],
                        hashed_password=hashed_password,
                        is_active=True,
                        is_verified=True,
                        is_superuser=False,
                        role=UserRole.ADVISOR.value,
                    )
                    session.add(new_user)
                    await session.flush()
                    # Initialize settings
                    await user_settings_repo.create_user_settings(user_id)
                    await session.commit()
                    logger.info(f'Created user with ID {user_id}')
            except Exception as e:
                await session.rollback()
                logger.error(f'Error creating user {row["email"]}: {e}')

            advisor_data = row.to_dict()
            advisor_data['advisor_id'] = uuid.UUID(advisor_data['advisor_id'])
            advisor_data['user_id'] = user_id
            advisors.append(Advisor(**advisor_data))

        def clean_row(row):
            """Convert NaN to None for database columns."""
            return {k: (None if pd.isna(v) else v) for k, v in row.items()}

        def parse_dt(val):
            """Parse datetime string or return None if NaN."""
            if pd.isna(val):
                return None
            try:
                dt = parser.parse(str(val))
                if dt.tzinfo is None:
                    from datetime import UTC

                    dt = dt.replace(tzinfo=UTC)
                return dt
            except Exception:
                return None

        print('Importing students...')
        stu_df = pd.read_csv('data/v2_students.csv')
        students = []
        for _, row in stu_df.iterrows():
            data = clean_row(row)
            data['sid'] = uuid.UUID(data['sid'])
            data['last_notified_timestamp'] = parse_dt(
                data.get('last_notified_timestamp')
            )
            students.append(Student(**data))

        print('Importing activities...')
        act_df = pd.read_csv('data/v2_activities.csv')
        activities = []
        for _, row in act_df.iterrows():
            data = clean_row(row)
            data['activity_id'] = uuid.UUID(data['activity_id'])
            data['sid'] = uuid.UUID(data['sid'])
            data['timestamp'] = parse_dt(data['timestamp'])
            activities.append(Activity(**data))

        print('Importing history...')
        hist_df = pd.read_csv('data/v2_student_status_history.csv')
        history = []
        for _, row in hist_df.iterrows():
            data = clean_row(row)
            data['history_id'] = uuid.UUID(data['history_id'])
            data['sid'] = uuid.UUID(data['sid'])
            data['status_recorded_at'] = parse_dt(data['status_recorded_at'])
            history.append(StudentStatusHistory(**data))

        session.add_all(students)
        session.add_all(activities)
        session.add_all(history)
        await session.flush()

        print('Importing advisors...')
        session.add_all(advisors)
        await session.flush()

        print('Importing cases...')
        case_df = pd.read_csv('data/v2_cases.csv')
        cases = []
        for _, row in case_df.iterrows():
            data = clean_row(row)
            data['case_id'] = uuid.UUID(data['case_id'])
            data['sid'] = uuid.UUID(data['sid'])
            data['assigned_advisor_id'] = uuid.UUID(data['assigned_advisor_id'])
            data['created_at'] = parse_dt(data['created_at'])
            data['closed_at'] = parse_dt(data.get('closed_at'))
            cases.append(Case(**data))
        session.add_all(cases)
        await session.flush()

        print('Importing emails...')
        email_df = pd.read_csv('data/v2_intervention_emails.csv')
        emails = []
        for _, row in email_df.iterrows():
            data = clean_row(row)
            data['email_id'] = uuid.UUID(data['email_id'])
            data['case_id'] = uuid.UUID(data['case_id'])
            data['created_at'] = parse_dt(data['created_at'])
            data['sent_at'] = parse_dt(data.get('sent_at'))
            emails.append(InterventionEmail(**data))
        session.add_all(emails)

        print('Importing ledger...')
        ledger_df = pd.read_csv('data/v2_point_ledger.csv')
        ledger = []
        for _, row in ledger_df.iterrows():
            data = clean_row(row)
            data['id'] = uuid.UUID(data['id'])
            data['advisor_id'] = uuid.UUID(data['advisor_id'])
            data['case_id'] = uuid.UUID(data['case_id'])
            data['earned_at'] = parse_dt(data['earned_at'])
            ledger.append(PointLedger(**data))
        session.add_all(ledger)

        print('Importing appointments...')
        appt_df = pd.read_csv('data/v2_appointments.csv')
        appts = []
        for _, row in appt_df.iterrows():
            data = clean_row(row)
            data['appointment_id'] = uuid.UUID(data['appointment_id'])
            data['case_id'] = uuid.UUID(data['case_id'])
            data['appointment_time'] = parse_dt(data['appointment_time'])
            data['created_at'] = parse_dt(data['created_at'])
            appts.append(Appointment(**data))
        session.add_all(appts)

        # Working hours
        for advisor in advisors:
            for day in range(5):
                session.add(
                    AdvisorWorkingHours(
                        id=generate_uuid(),
                        advisor_id=advisor.advisor_id,
                        day_of_week=day,
                        start_time=time(9, 0),
                        end_time=time(17, 0),
                    )
                )

        await session.commit()
    print('Reseed dashboard complete.')


def main():
    parser = argparse.ArgumentParser(
        description='Reseed database with dashboard mock data.'
    )
    parser.add_argument(
        'command',
        nargs='?',
        default='run',
        choices=['run', 'reset'],
        help='Command to run (run or reset)',
    )
    args = parser.parse_args()

    reset = args.command == 'reset'
    asyncio.run(reseed_dashboard(reset=reset))


if __name__ == '__main__':
    main()
