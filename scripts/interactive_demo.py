"""
Interactive Demo Script for Admin Dashboard.
Sequentially updates data through 3 phases and prints expected metrics.
"""

import asyncio
import os
import random
import sys
import subprocess
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from faker import Faker
from sqlalchemy import select

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.identifiers import generate_uuid
from src.domain.value_objects.status import (
    InterventionStatus,
    RiskReason,
    RiskStatus,
    EmailStatus,
)
from src.infrastructure.database.models import (
    Activity,
    Advisor,
    Case,
    InterventionEmail,
    PointLedger,
    Student,
    StudentStatusHistory,
    User,
)
from src.infrastructure.database.session import async_session_maker
from src.domain.services.anomaly_engine.zscore import ZScore
from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
    SqlAlchemyActivityRepository,
    SqlAlchemyStatusHistoryRepository,
    SqlAlchemyStudentRepository,
    SqlAlchemyUserSettingsRepository,
)
from src.presentation.api.auth import SQLAlchemyUserDatabase, UserManager, UserRole
from src.infrastructure.persistence.sqlalchemy_uow import SqlAlchemyUnitOfWork

# Constants
fake = Faker()
NUM_STUDENTS = 60
NUM_ADVISORS = 5
START_DATE = datetime(2026, 1, 5, tzinfo=UTC)

COURSES = [
    {'id': 'CS101', 'name': 'Programming Fundamentals'},
    {'id': 'MATH201', 'name': 'Advanced Calculus'},
    {'id': 'ENG102', 'name': 'Western Literature'},
    {'id': 'PSYC101', 'name': 'Intro to Psychology'},
]


async def run_anomaly_detection(session):
    """Run Z-Score anomaly detection and update history/status."""
    activity_repo = SqlAlchemyActivityRepository(session)
    history_repo = SqlAlchemyStatusHistoryRepository(session)
    student_repo = SqlAlchemyStudentRepository(session)

    weekly_avgs = await activity_repo.get_weekly_averages()
    existing_history = await history_repo.get_all_history()
    history_set = {
        (h['sid'], h['academic_year'], h['semester'], h['week'])
        for h in existing_history
    }

    student_data = defaultdict(list)
    for avg in weekly_avgs:
        student_data[avg['sid']].append(avg)

    engine = ZScore()
    new_history_records, risk_statuses = engine.run(student_data, history_set)

    if new_history_records:
        await history_repo.batch_create_history(new_history_records)

    for sid, latest_risk in risk_statuses.items():
        student = await student_repo.get_by_id(sid)
        if student and student.current_risk_status != latest_risk:
            student.current_risk_status = latest_risk
            await student_repo.save(student)

    return risk_statuses


async def clear_db():
    """Wipe database and run migrations."""
    print('Wiping database schema...')
    from sqlalchemy import text
    from src.core.config import config
    from sqlalchemy.ext.asyncio import create_async_engine

    url = config.database_url
    if 'postgresql+asyncpg' not in url:
        url = url.replace('postgresql://', 'postgresql+asyncpg://')

    engine = create_async_engine(url, isolation_level='AUTOCOMMIT')
    async with engine.connect() as conn:
        try:
            # Terminate active connections to allow dropping schema
            await conn.execute(
                text("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = current_database() 
                AND pid <> pg_backend_pid();
            """)
            )
        except Exception as e:
            print(f'Warning: Could not terminate connections: {e}')

        await conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE;'))
        await conn.execute(text('CREATE SCHEMA public;'))
        await conn.execute(text('GRANT ALL ON SCHEMA public TO public;'))
    await engine.dispose()

    print('Running migrations...')
    subprocess.run(['uv', 'run', 'alembic', 'upgrade', 'head'], check=True)


async def setup_advisors(session):
    """Ensure admin and multiple advisor users/records exist."""
    user_db = SQLAlchemyUserDatabase(session, User)
    settings_repo = SqlAlchemyUserSettingsRepository(session)
    uow = SqlAlchemyUnitOfWork(session)
    user_manager = UserManager(user_db, settings_repo, uow)

    # 1. Ensure Admin User

    stmt = select(User).where(User.email == 'dev@gmail.com')
    admin_user = (await session.execute(stmt)).scalar_one_or_none()

    if not admin_user:
        print('Creating admin user (dev@gmail.com / dev)...')
        hashed_password = user_manager.password_helper.hash('dev')
        admin_user = User(
            id=generate_uuid(),
            email='dev@gmail.com',
            hashed_password=hashed_password,
            is_active=True,
            is_verified=True,
            is_superuser=True,
            role=UserRole.ADMIN.value,
        )
        session.add(admin_user)
        await session.flush()
        await settings_repo.create_user_settings(admin_user.id)

    # 2. Ensure Multiple Advisors
    advisors = []
    advisor_titles = [
        'Senior Advisor',
        'Academic Coach',
        'Student Success Specialist',
        'Department Head',
        'Guidance Counselor',
    ]

    for i in range(NUM_ADVISORS):
        email = f'adv{i + 1}@example.com'
        stmt = select(User).where(User.email == email)
        adv_user = (await session.execute(stmt)).scalar_one_or_none()

        if not adv_user:
            print(f'Creating advisor user ({email} / password)...')
            user_id = generate_uuid()
            hashed_password = user_manager.password_helper.hash('password')
            adv_user = User(
                id=user_id,
                email=email,
                hashed_password=hashed_password,
                is_active=True,
                is_verified=True,
                is_superuser=False,
                role=UserRole.ADVISOR.value,
            )
            session.add(adv_user)
            await session.flush()
            await settings_repo.create_user_settings(user_id)
        else:
            user_id = adv_user.id

        stmt = select(Advisor).where(Advisor.user_id == user_id)
        advisor = (await session.execute(stmt)).scalar_one_or_none()
        if not advisor:
            adv_name = fake.name()
            print(f'Creating advisor record: {adv_name}...')
            advisor = Advisor(
                advisor_id=generate_uuid(),
                name=adv_name,
                email=email,
                title=random.choice(advisor_titles),
                user_id=user_id,
            )
            session.add(advisor)
            await session.flush()
        advisors.append(advisor)

    return advisors


async def main():
    print('\n' + '=' * 50)
    print('   ADMIN DASHBOARD INTERACTIVE DEMO   ')
    print('=' * 50)

    # Step 0: Reset
    await clear_db()

    async with async_session_maker() as session:
        advisors = await setup_advisors(session)
        advisor_ids = [a.advisor_id for a in advisors]

        # Step 1: Baseline
        print('\n[STEP 1] Phase 1: Baseline (Weeks 1-4)')
        print(f'Creating {NUM_STUDENTS} healthy students with high scores...')
        students = []
        majors = [
            'Computer Science',
            'Business Administration',
            'Psychology',
            'Mechanical Engineering',
            'Biology',
        ]

        for i in range(NUM_STUDENTS):
            sid = generate_uuid()
            name = fake.name()
            email = f'{name.lower().replace(" ", ".")}@example.edu'
            student = Student(
                sid=sid,
                student_name=name,
                email=email,
                major=random.choice(majors),
                current_risk_status=RiskStatus.NORMAL,
                cumulative_gpa=round(random.uniform(3.2, 3.9), 2),
            )
            session.add(student)
            students.append(student)
        await session.flush()
        sids = [s.sid for s in students]

        for week in range(1, 5):
            for sid in sids:
                for course in COURSES:
                    session.add(
                        Activity(
                            activity_id=generate_uuid(),
                            sid=sid,
                            course_id=course['id'],
                            course_name=course['name'],
                            test_type='Quiz',
                            score=random.randint(75, 98),  # Slight noise
                            timestamp=START_DATE + timedelta(weeks=week - 1),
                            academic_year=2026,
                            semester=1,
                            week=week,
                        )
                    )
        await session.commit()
        await run_anomaly_detection(session)

        print('\n>>> Phase 1 Complete.')
        print('Expected Metrics on Dashboard:')
        print('---------------------------------')
        print('Priority Queue:  0')
        print('Response KPI:    N/A')
        print('Activation Rate: 0.0%')
        print('Recovery Rate:   0.0%')
        print('Impact XP:       0')
        print('---------------------------------')
        print(
            '\nLOG IN AS: dev@gmail.com / dev (ADMIN) or adv1@example.com / password (ADVISOR)'
        )
        input(
            '\nRefresh the dashboard and verify. Then press Enter to proceed to Phase 2...'
        )

        # Step 2: Performance Drop
        print('\n[STEP 2] Phase 2: Performance Drop (Weeks 5-8)')
        num_dropping = 15
        print(f'Simulating drop for {num_dropping} students with diverse profiles...')

        # Select students to drop
        dropping_sids = sids[:num_dropping]
        dropping_config = {}

        for i, sid in enumerate(dropping_sids):
            if i < 5:  # Profile 1: Single Subject Crash (STEM)
                dropping_config[sid] = [COURSES[0]['id']]
            elif i < 10:  # Profile 2: Systemic Drop (3 subjects)
                dropping_config[sid] = [
                    COURSES[0]['id'],
                    COURSES[1]['id'],
                    COURSES[2]['id'],
                ]
            else:  # Profile 3: Borderline/Elevated (All subjects drop to 50-60)
                dropping_config[sid] = [c['id'] for c in COURSES]

        for week in range(5, 9):
            for sid in sids:
                for course in COURSES:
                    if sid in dropping_config:
                        courses_to_drop = dropping_config[sid]
                        if course['id'] in courses_to_drop:
                            if len(courses_to_drop) == len(COURSES):  # Profile 3
                                score = random.randint(50, 65)
                            else:  # Profiles 1 & 2
                                score = random.randint(15, 35)
                        else:
                            score = random.randint(75, 98)
                    else:
                        score = random.randint(75, 98)

                    session.add(
                        Activity(
                            activity_id=generate_uuid(),
                            sid=sid,
                            course_id=course['id'],
                            course_name=course['name'],
                            test_type='Quiz',
                            score=score,
                            timestamp=START_DATE + timedelta(weeks=week - 1),
                            academic_year=2026,
                            semester=1,
                            week=week,
                        )
                    )
        await session.commit()
        await run_anomaly_detection(session)

        print(
            'Creating cases and performing advisor actions with varying response times...'
        )

        # Simulate advisor actions
        for i, sid in enumerate(dropping_sids):
            # Assign to different advisors
            adv_id = advisor_ids[i % NUM_ADVISORS]
            case_id = generate_uuid()

            # Determine initial GPA for academic impact
            stmt_s = select(Student).where(Student.sid == sid)
            student_obj = (await session.execute(stmt_s)).scalar_one()
            initial_gpa = student_obj.cumulative_gpa

            new_case = Case(
                case_id=case_id,
                sid=sid,
                risk_reason=RiskReason.GRADE_DROP,
                intervention_status=InterventionStatus.NEW,
                created_at=START_DATE + timedelta(weeks=8, days=1),
                assigned_advisor_id=adv_id,
                initial_gpa=initial_gpa,
                version=1,
            )
            session.add(new_case)

            # Varying advisor response time
            if i % 3 == 0:  # Fast advisor
                lead_time_hours = random.uniform(0.5, 2.0)
            elif i % 3 == 1:  # Average advisor
                lead_time_hours = random.uniform(2.0, 8.0)
            else:  # Slow advisor
                lead_time_hours = random.uniform(8.0, 24.0)

            accepted_at = new_case.created_at + timedelta(hours=lead_time_hours)
            new_case.assigned_at = accepted_at
            new_case.first_interaction_at = accepted_at

            session.add(
                PointLedger(
                    id=generate_uuid(),
                    advisor_id=adv_id,
                    case_id=case_id,
                    action='accept_case',
                    points=10,
                    earned_at=accepted_at,
                )
            )

            # Send nudge
            sent_at = accepted_at + timedelta(hours=random.uniform(0.1, 1.0))
            session.add(
                InterventionEmail(
                    email_id=generate_uuid(),
                    case_id=case_id,
                    status=EmailStatus.SENT,
                    is_nudge=True,
                    created_at=sent_at,
                    sent_at=sent_at,
                    subject='Checking in on your academic progress',
                    body=f'Hi {student_obj.student_name}, we noticed some changes in your recent scores...',
                )
            )
            session.add(
                PointLedger(
                    id=generate_uuid(),
                    advisor_id=adv_id,
                    case_id=case_id,
                    action='send_nudge',
                    points=15,
                    earned_at=sent_at,
                )
            )
            new_case.intervention_status = InterventionStatus.SENT

        await session.commit()

        print('\n>>> Phase 2 Complete.')
        print('Expected Metrics on Dashboard:')
        print('---------------------------------')
        print(
            f'Priority Queue:  {num_dropping} (Critical/Elevated risk students with active cases)'
        )
        print('Response KPI:    ~8-10 hours (Average across fast/avg/slow advisors)')
        print("Activation Rate: 0.0% (Nudges sent but students haven't engaged yet)")
        print('Recovery Rate:   0.0%')
        print(f'Impact XP:       {num_dropping * 25} (Accept + Nudge points)')
        print('---------------------------------')
        input(
            '\nRefresh the dashboard and verify. Then press Enter to proceed to Phase 3...'
        )

        # Step 3: Recovery
        print('\n[STEP 3] Phase 3: Recovery & Intervention (Weeks 9-12)')
        num_recovering = 10
        print(
            f'Simulating recovery for {num_recovering} students and persistent risk for {num_dropping - num_recovering}...'
        )

        recovering_sids = dropping_sids[:num_recovering]
        still_at_risk_sids = dropping_sids[num_recovering:]

        for week in range(9, 13):
            for sid in sids:
                for course in COURSES:
                    if sid in recovering_sids:
                        score = random.randint(80, 95)  # Back to normal
                    elif (
                        sid in still_at_risk_sids
                        and sid in dropping_config
                        and course['id'] in dropping_config[sid]
                    ):
                        score = random.randint(15, 35)  # Still failing
                    else:
                        score = random.randint(75, 98)

                    session.add(
                        Activity(
                            activity_id=generate_uuid(),
                            sid=sid,
                            course_id=course['id'],
                            course_name=course['name'],
                            test_type='Quiz',
                            score=score,
                            timestamp=START_DATE + timedelta(weeks=week - 1),
                            academic_year=2026,
                            semester=1,
                            week=week,
                        )
                    )

        await session.commit()
        final_risks = await run_anomaly_detection(session)

        # Resolve Cases and simulate engagement
        for i, sid in enumerate(dropping_sids):
            stmt = select(Case).where(
                Case.sid == sid, Case.intervention_status != InterventionStatus.RESOLVED
            )
            case_obj = (await session.execute(stmt)).scalar_one_or_none()
            if not case_obj:
                continue

            # Simulate student response for Activation Rate
            if i % 5 != 0:  # 80% engagement rate
                case_obj.responded_at = case_obj.assigned_at + timedelta(
                    days=random.uniform(1, 3)
                )
                stmt_email = select(InterventionEmail).where(
                    InterventionEmail.case_id == case_obj.case_id
                )
                email_obj = (await session.execute(stmt_email)).scalar_one_or_none()
                if email_obj:
                    email_obj.responded_at = case_obj.responded_at

            # Resolve cases for recovered students
            if sid in recovering_sids:
                case_obj.intervention_status = InterventionStatus.RESOLVED
                case_obj.closed_at = START_DATE + timedelta(weeks=12, days=1)
                case_obj.final_gpa = round(
                    case_obj.initial_gpa + random.uniform(-0.1, 0.2), 2
                )

                session.add(
                    PointLedger(
                        id=generate_uuid(),
                        advisor_id=case_obj.assigned_advisor_id,
                        case_id=case_obj.case_id,
                        action='resolve_case',
                        points=50,
                        earned_at=case_obj.closed_at,
                    )
                )

        await session.commit()

        print('\n>>> Phase 3 Complete.')
        print('Final Status Summary:')
        num_recovered = sum(
            1 for sid in recovering_sids if final_risks.get(sid) == RiskStatus.NORMAL
        )
        num_still_risk = sum(
            1 for sid in still_at_risk_sids if final_risks.get(sid) != RiskStatus.NORMAL
        )
        print(f' - Students Recovered: {num_recovered}')
        print(f' - Students Still At Risk: {num_still_risk}')

        print('\nExpected Metrics on Dashboard:')
        print('---------------------------------')
        print(f'Priority Queue:  {num_still_risk} (Persistent at-risk students)')
        print('Response KPI:    ~8-10 hours (Unchanged)')
        print(
            f'Activation Rate: {((num_dropping - 3) / num_dropping * 100):.1f}% (Approx based on 80% engagement)'
        )
        print(f'Recovery Rate:   {(num_recovered / num_dropping * 100):.1f}%')
        print(
            f'Impact XP:       {num_dropping * 25 + num_recovered * 50} (Phase 2 points + Resolutions)'
        )
        print('---------------------------------')
        print('\nDemo Complete! You can now explore the final state on the dashboard.')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\nDemo cancelled by user.')
        sys.exit(0)
    except Exception as e:
        print(f'\nError: {e}')
        import traceback

        traceback.print_exc()
        sys.exit(1)
