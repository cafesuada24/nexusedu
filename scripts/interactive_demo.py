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
ADVISOR_ID = '3a42d761-0e11-45c8-81bb-d0cde691fc5b'
NUM_STUDENTS = 20
START_DATE = datetime(2026, 1, 5, tzinfo=UTC)

COURSES = [
    {"id": "CS101", "name": "Programming Fundamentals"},
    {"id": "MATH201", "name": "Advanced Calculus"},
    {"id": "ENG102", "name": "Western Literature"},
    {"id": "PSYC101", "name": "Intro to Psychology"},
]

async def run_anomaly_detection(session):
    """Run Z-Score anomaly detection and update history/status."""
    activity_repo = SqlAlchemyActivityRepository(session)
    history_repo = SqlAlchemyStatusHistoryRepository(session)
    student_repo = SqlAlchemyStudentRepository(session)

    weekly_avgs = await activity_repo.get_weekly_averages()
    existing_history = await history_repo.get_all_history()
    history_set = {(h['sid'], h['academic_year'], h['semester'], h['week']) for h in existing_history}

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
    print("Wiping database schema...")
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
            await conn.execute(text("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = current_database() 
                AND pid <> pg_backend_pid();
            """))
        except Exception as e:
            print(f"Warning: Could not terminate connections: {e}")
            
        await conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE;'))
        await conn.execute(text('CREATE SCHEMA public;'))
        await conn.execute(text('GRANT ALL ON SCHEMA public TO public;'))
    await engine.dispose()

    print("Running migrations...")
    subprocess.run(["uv", "run", "alembic", "upgrade", "head"], check=True)

async def setup_advisor(session):
    """Ensure advisor user and record exist."""
    user_db = SQLAlchemyUserDatabase(session, User)
    settings_repo = SqlAlchemyUserSettingsRepository(session)
    uow = SqlAlchemyUnitOfWork(session)
    user_manager = UserManager(user_db, settings_repo, uow)

    # Check if admin user exists
    from sqlalchemy import select
    stmt = select(User).where(User.email == "dev@gmail.com")
    existing_user = (await session.execute(stmt)).scalar_one_or_none()
    
    if not existing_user:
        # Create admin user
        print("Creating admin user (dev@gmail.com / dev)...")
        hashed_password = user_manager.password_helper.hash("dev")
        admin_user = User(
            id=generate_uuid(),
            email="dev@gmail.com",
            hashed_password=hashed_password,
            is_active=True,
            is_verified=True,
            is_superuser=True,
            role=UserRole.ADMIN.value,
        )
        session.add(admin_user)
        await session.flush()
        await settings_repo.create_user_settings(admin_user.id)

    # Check if advisor user exists
    stmt = select(User).where(User.email == "adv@example.com")
    existing_adv_user = (await session.execute(stmt)).scalar_one_or_none()
    
    if not existing_adv_user:
        print("Creating advisor user (adv@example.com / password)...")
        user_id = generate_uuid()
        hashed_password = user_manager.password_helper.hash("password")
        new_user = User(
            id=user_id,
            email="adv@example.com",
            hashed_password=hashed_password,
            is_active=True,
            is_verified=True,
            is_superuser=False,
            role=UserRole.ADVISOR.value,
        )
        session.add(new_user)
        await session.flush()
        await settings_repo.create_user_settings(user_id)
    else:
        user_id = existing_adv_user.id

    # Check if advisor record exists
    stmt = select(Advisor).where(Advisor.advisor_id == ADVISOR_ID)
    advisor = (await session.execute(stmt)).scalar_one_or_none()
    if not advisor:
        print(f"Creating advisor record with ID {ADVISOR_ID}...")
        advisor = Advisor(
            advisor_id=ADVISOR_ID,
            name="Demo Advisor",
            email="adv@example.com",
            title="Senior Advisor",
            user_id=user_id
        )
        session.add(advisor)
        await session.flush()
    
    return advisor

async def main():
    print("\n" + "="*50)
    print("   ADMIN DASHBOARD INTERACTIVE DEMO   ")
    print("="*50)

    # Step 0: Reset
    await clear_db()
    
    async with async_session_maker() as session:
        advisor = await setup_advisor(session)
        
        # Step 1: Baseline
        print("\n[STEP 1] Phase 1: Baseline (Weeks 1-4)")
        print("Creating 20 healthy students with high scores...")
        students = []
        for i in range(NUM_STUDENTS):
            sid = generate_uuid()
            student = Student(
                sid=sid,
                student_name=f'Student {chr(65+i)}',
                email=f'student_{i}@example.edu',
                major='Computer Science' if i % 2 == 0 else 'Business',
                current_risk_status=RiskStatus.NORMAL,
                cumulative_gpa=3.5
            )
            session.add(student)
            students.append(student)
        await session.flush()
        sids = [s.sid for s in students]

        for week in range(1, 5):
            for sid in sids:
                for course in COURSES:
                    session.add(Activity(
                        activity_id=generate_uuid(),
                        sid=sid,
                        course_id=course["id"],
                        course_name=course["name"],
                        test_type='Quiz',
                        score=random.randint(80, 95),
                        timestamp=START_DATE + timedelta(weeks=week-1),
                        academic_year=2026,
                        semester=1,
                        week=week,
                    ))
        await session.commit()
        await run_anomaly_detection(session)
        
        print("\n>>> Phase 1 Complete.")
        print("Expected Metrics on Dashboard:")
        print("---------------------------------")
        print("Priority Queue:  0")
        print("Response KPI:    N/A")
        print("Activation Rate: 0.0%")
        print("Recovery Rate:   0.0%")
        print("Impact XP:       0")
        print("---------------------------------")
        print("\nLOG IN AS: dev@gmail.com / dev (ADMIN) or adv@example.com / password (ADVISOR)")
        input("\nRefresh the dashboard and verify. Then press Enter to proceed to Phase 2...")

        # Step 2: Performance Drop
        print("\n[STEP 2] Phase 2: Performance Drop (Weeks 5-8)")
        print("Simulating drop for 5 students (A, B, C, D, E)...")
        
        dropping_config = {
            sids[0]: [COURSES[0]["id"]], 
            sids[1]: [COURSES[0]["id"], COURSES[1]["id"], COURSES[2]["id"]], 
            sids[2]: [COURSES[0]["id"], COURSES[3]["id"]], 
            sids[3]: [COURSES[1]["id"]], 
            sids[4]: [c["id"] for c in COURSES], 
        }
        dropping_sids = list(dropping_config.keys())

        for week in range(5, 9):
            for sid in sids:
                for course in COURSES:
                    if sid in dropping_config and course["id"] in dropping_config[sid]:
                        score = random.randint(15, 35)
                    else:
                        score = random.randint(80, 95)
                    
                    session.add(Activity(
                        activity_id=generate_uuid(),
                        sid=sid,
                        course_id=course["id"],
                        course_name=course["name"],
                        test_type='Quiz',
                        score=score,
                        timestamp=START_DATE + timedelta(weeks=week-1),
                        academic_year=2026,
                        semester=1,
                        week=week,
                    ))
        await session.commit()
        await run_anomaly_detection(session)

        print("Creating cases and performing advisor actions...")
        # Re-fetch advisor to ensure it's in the current session
        from sqlalchemy import select
        advisor = (await session.execute(select(Advisor).where(Advisor.advisor_id == ADVISOR_ID))).scalar_one()

        for sid in dropping_sids:
            case_id = generate_uuid()
            new_case = Case(
                case_id=case_id,
                sid=sid,
                risk_reason=RiskReason.GRADE_DROP,
                intervention_status=InterventionStatus.NEW,
                created_at=START_DATE + timedelta(weeks=8, days=1),
                assigned_advisor_id=ADVISOR_ID,
                initial_gpa=3.5, # Required for Academic Impact
                version=1,
            )
            session.add(new_case)
            
            # Advisor accepts case after 2 hours
            accepted_at = new_case.created_at + timedelta(hours=2)
            new_case.assigned_at = accepted_at
            new_case.first_interaction_at = accepted_at # Required for Admin Lead Time
            
            session.add(PointLedger(
                id=generate_uuid(),
                advisor_id=ADVISOR_ID,
                case_id=case_id,
                action="accept_case",
                points=10,
                earned_at=accepted_at
            ))
            
            # Advisor sends nudge after another 1 hour (Total 3h from creation)
            sent_at = accepted_at + timedelta(hours=1)
            session.add(InterventionEmail(
                email_id=generate_uuid(),
                case_id=case_id,
                status=EmailStatus.SENT,
                is_nudge=True, # Required for Admin Nudge Activation
                created_at=sent_at,
                sent_at=sent_at,
                subject="Checking in on your progress",
                body="Hi, we noticed a change in your scores..."
            ))
            session.add(PointLedger(
                id=generate_uuid(),
                advisor_id=ADVISOR_ID,
                case_id=case_id,
                action="send_nudge",
                points=15,
                earned_at=sent_at
            ))
            new_case.intervention_status = InterventionStatus.SENT

        await session.commit()
        
        print("\n>>> Phase 2 Complete.")
        print("Expected Metrics on Dashboard:")
        print("---------------------------------")
        print("Priority Queue:  5 (Critical/Elevated risk students with active cases)")
        print("Response KPI:    ~2.0 hours (Time to 'accept_case')")
        print("Activation Rate: 0.0% (Nudges sent but students haven't engaged yet)")
        print("Recovery Rate:   0.0%")
        print("Impact XP:       125 (5 cases * (10 accept + 15 nudge))")
        print("---------------------------------")
        input("\nRefresh the dashboard and verify. Then press Enter to proceed to Phase 3...")

        # Step 3: Recovery
        print("\n[STEP 3] Phase 3: Recovery & Intervention (Weeks 9-12)")
        print("Simulating recovery for Students A, B, C...")
        
        recovering_sids = sids[:3]
        still_at_risk_sids = sids[3:5]
        
        for week in range(9, 13):
            for sid in sids:
                for course in COURSES:
                    if sid in recovering_sids:
                        score = random.randint(85, 98)
                    elif sid in still_at_risk_sids and sid in dropping_config and course["id"] in dropping_config[sid]:
                        score = random.randint(15, 35)
                    else:
                        score = random.randint(80, 95)
                    
                    session.add(Activity(
                        activity_id=generate_uuid(),
                        sid=sid,
                        course_id=course["id"],
                        course_name=course["name"],
                        test_type='Quiz',
                        score=score,
                        timestamp=START_DATE + timedelta(weeks=week-1),
                        academic_year=2026,
                        semester=1,
                        week=week,
                    ))

        await session.commit()
        final_risks = await run_anomaly_detection(session)

        # Resolve Cases for recovered students
        for sid in recovering_sids:
            stmt = select(Case).where(Case.sid == sid, Case.intervention_status != InterventionStatus.RESOLVED)
            case_obj = (await session.execute(stmt)).scalar_one_or_none()
            if case_obj:
                case_obj.intervention_status = InterventionStatus.RESOLVED
                case_obj.closed_at = START_DATE + timedelta(weeks=12, days=1)
                case_obj.final_gpa = 3.6 # Show improvement for Academic Impact
                
                # Simulate student response for Nudge Activation
                stmt_email = select(InterventionEmail).where(InterventionEmail.case_id == case_obj.case_id)
                email_obj = (await session.execute(stmt_email)).scalar_one_or_none()
                if email_obj:
                    email_obj.responded_at = case_obj.closed_at - timedelta(days=2)

                session.add(PointLedger(
                    id=generate_uuid(),
                    advisor_id=ADVISOR_ID,
                    case_id=case_obj.case_id,
                    action="resolve_case",
                    points=50,
                    earned_at=case_obj.closed_at
                ))
        
        await session.commit()

        print("\n>>> Phase 3 Complete.")
        print("Final Student Statuses:")
        for i, sid in enumerate(sids[:5]):
            name = f"Student {chr(65+i)}"
            status = final_risks.get(sid, "Unknown")
            print(f" - {name}: {status}")

        print("\nExpected Metrics on Dashboard:")
        print("---------------------------------")
        print("Priority Queue:  2 (Students D & E remain at risk)")
        print("Response KPI:    ~2.0 hours (Unchanged)")
        print("Activation Rate: 60.0% (3 out of 5 cases resolved/responded)")
        print("Recovery Rate:   60.0% (3 out of 5 at-risk students stabilized)")
        print("Impact XP:       275 (125 from Phase 2 + 3 * 50 for resolution)")
        print("---------------------------------")
        print("\nDemo Complete! You can now explore the final state on the dashboard.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
