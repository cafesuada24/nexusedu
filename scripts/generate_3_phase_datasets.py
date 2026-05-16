"""
Script to generate a 3-phase dataset with MULTIPLE SUBJECTS for the Admin Dashboard.
Phase 1: Baseline (Weeks 1-4)
Phase 2: Performance Drop (Weeks 5-8) - Some students drop in MULTIPLE subjects (Systemic Breadth)
Phase 3: Recovery & Intervention (Weeks 9-12)
"""

import asyncio
import os
import random
import sys
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import select, delete

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.identifiers import generate_uuid
from src.domain.value_objects.status import (
    InterventionStatus,
    RiskReason,
    RiskStatus,
)
from src.infrastructure.database.models import (
    Activity,
    Advisor,
    Case,
    InterventionEmail,
    PointLedger,
    Student,
    StudentStatusHistory,
    Base,
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

# Multi-subject configuration
COURSES = [
    {"id": "CS101", "name": "Programming Fundamentals"}, # STEM
    {"id": "MATH201", "name": "Advanced Calculus"},     # STEM
    {"id": "ENG102", "name": "Western Literature"},      # Humanities
    {"id": "PSYC101", "name": "Intro to Psychology"},   # Social Sciences
]

async def run_anomaly_detection(session):
    """Run Z-Score anomaly detection and update history/status."""
    activity_repo = SqlAlchemyActivityRepository(session)
    history_repo = SqlAlchemyStatusHistoryRepository(session)
    student_repo = SqlAlchemyStudentRepository(session)

    # Fetch all data
    weekly_avgs = await activity_repo.get_weekly_averages()
    existing_history = await history_repo.get_all_history()
    history_set = {(h['sid'], h['academic_year'], h['semester'], h['week']) for h in existing_history}

    student_data = defaultdict(list)
    for avg in weekly_avgs:
        student_data[avg['sid']].append(avg)

    # Detect
    engine = ZScore()
    new_history_records, risk_statuses = engine.run(student_data, history_set)

    if new_history_records:
        await history_repo.batch_create_history(new_history_records)

    # Update student current status
    for sid, latest_risk in risk_statuses.items():
        student = await student_repo.get_by_id(sid)
        if student and student.current_risk_status != latest_risk:
            student.current_risk_status = latest_risk
            await student_repo.save(student)

async def export_phase_csv(session, phase_num, activity_ids_this_phase):
    """Export current students and activities for the given phase to CSV."""
    os.makedirs('data/phases', exist_ok=True)
    
    # Export Students
    stmt_students = select(Student)
    students_res = (await session.execute(stmt_students)).scalars().all()
    student_dicts = []
    for s in students_res:
        student_dicts.append({
            'sid': str(s.sid),
            'student_name': s.student_name,
            'email': s.email,
            'major': s.major,
            'current_risk_status': s.current_risk_status.value if hasattr(s.current_risk_status, 'value') else s.current_risk_status,
            'cumulative_gpa': s.cumulative_gpa,
            'last_notified_timestamp': s.last_notified_timestamp.isoformat() if s.last_notified_timestamp else None
        })
    pd.DataFrame(student_dicts).to_csv(f'data/phases/students_phase{phase_num}.csv', index=False)
    
    # Export Activities (Only for this phase)
    stmt_activities = select(Activity).where(Activity.activity_id.in_(activity_ids_this_phase))
    activities_res = (await session.execute(stmt_activities)).scalars().all()
    activity_dicts = []
    for a in activities_res:
        activity_dicts.append({
            'activity_id': str(a.activity_id),
            'sid': str(a.sid),
            'course_id': a.course_id,
            'course_name': a.course_name,
            'test_type': a.test_type,
            'score': a.score,
            'timestamp': a.timestamp.isoformat(),
            'academic_year': a.academic_year,
            'semester': a.semester,
            'week': a.week
        })
    pd.DataFrame(activity_dicts).to_csv(f'data/phases/activities_phase{phase_num}.csv', index=False)
    print(f"Exported Phase {phase_num} CSVs to data/phases/")

async def clear_db():
    """Clear relevant tables for a fresh start."""
    print("Clearing existing data...")
    async with async_session_maker() as session:
        await session.execute(delete(PointLedger))
        await session.execute(delete(InterventionEmail))
        await session.execute(delete(Case))
        await session.execute(delete(StudentStatusHistory))
        await session.execute(delete(Activity))
        await session.execute(delete(Student))
        await session.commit()

async def generate_3_phases():
    await clear_db()
    
    async with async_session_maker() as session:
        # Create Advisor and User if not exists
        user_id = generate_uuid()
        user_db = SQLAlchemyUserDatabase(session, User)
        settings_repo = SqlAlchemyUserSettingsRepository(session)
        uow = SqlAlchemyUnitOfWork(session)
        user_manager = UserManager(user_db, settings_repo, uow)

        # Check if user exists
        stmt = select(User).where(User.email == "adv@example.com")
        existing_user = (await session.execute(stmt)).scalar_one_or_none()
        
        if not existing_user:
            print("Creating advisor user...")
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
            user_id = existing_user.id

        stmt = select(Advisor).where(Advisor.advisor_id == ADVISOR_ID)
        advisor = (await session.execute(stmt)).scalar_one_or_none()
        if not advisor:
            print("Creating advisor record...")
            advisor = Advisor(
                advisor_id=ADVISOR_ID,
                name="Demo Advisor",
                email="adv@example.com",
                title="Senior Advisor",
                user_id=user_id
            )
            session.add(advisor)
            await session.flush()
        else:
            advisor.user_id = user_id

        # 1. Create 20 Students
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

        # --- PHASE 1: BASELINE (Weeks 1-4) ---
        print("Phase 1: Generating baseline (Weeks 1-4) for 4 subjects...")
        phase1_activity_ids = []
        for week in range(1, 5):
            for sid in sids:
                for course in COURSES:
                    aid = generate_uuid()
                    phase1_activity_ids.append(aid)
                    session.add(Activity(
                        activity_id=aid,
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
        await export_phase_csv(session, 1, phase1_activity_ids)
        print("Phase 1 Complete.")

        # --- PHASE 2: DROP (Weeks 5-8) ---
        print("Phase 2: Generating drop (Weeks 5-8) with SYSTEMIC risk patterns...")
        phase2_activity_ids = []
        # Profiles for dropping students
        # Student A: Single subject drop (CS101)
        # Student B: Systemic drop (3 subjects: CS, MATH, ENG)
        # Student C: Moderate Systemic (2 subjects: CS, PSYC)
        # Student D: Single subject (MATH201)
        # Student E: Full Systemic (All 4 subjects)
        
        dropping_config = {
            sids[0]: [COURSES[0]["id"]], # Student A
            sids[1]: [COURSES[0]["id"], COURSES[1]["id"], COURSES[2]["id"]], # Student B (Systemic)
            sids[2]: [COURSES[0]["id"], COURSES[3]["id"]], # Student C (Moderate Systemic)
            sids[3]: [COURSES[1]["id"]], # Student D
            sids[4]: [c["id"] for c in COURSES], # Student E (Full Systemic)
        }
        dropping_sids = list(dropping_config.keys())

        for week in range(5, 9):
            for sid in sids:
                for course in COURSES:
                    aid = generate_uuid()
                    phase2_activity_ids.append(aid)
                    
                    if sid in dropping_config and course["id"] in dropping_config[sid]:
                        score = random.randint(15, 35) # CRASH
                    else:
                        score = random.randint(80, 95)
                    
                    session.add(Activity(
                        activity_id=aid,
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
        
        # Create Cases for dropping students
        for sid in dropping_sids:
            case_id = generate_uuid()
            new_case = Case(
                case_id=case_id,
                sid=sid,
                risk_reason=RiskReason.GRADE_DROP,
                intervention_status=InterventionStatus.NEW,
                created_at=START_DATE + timedelta(weeks=8, days=1),
                assigned_advisor_id=ADVISOR_ID,
                version=1,
            )
            session.add(new_case)
            
            accepted_at = new_case.created_at + timedelta(hours=2)
            session.add(PointLedger(
                id=generate_uuid(),
                advisor_id=ADVISOR_ID,
                case_id=case_id,
                action="accept_case",
                points=10,
                earned_at=accepted_at
            ))
            
            sent_at = accepted_at + timedelta(hours=1)
            session.add(InterventionEmail(
                email_id=generate_uuid(),
                case_id=case_id,
                status="sent",
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
        await run_anomaly_detection(session)
        await export_phase_csv(session, 2, phase2_activity_ids)
        print("Phase 2 Complete. Systemic patterns created for Students B, C, E.")

        # --- PHASE 3: RECOVERY (Weeks 9-12) ---
        print("Phase 3: Generating recovery (Weeks 9-12)...")
        phase3_activity_ids = []
        recovering_sids = sids[:3] # Students A, B, C recover
        still_at_risk_sids = sids[3:5] # Students D, E stay low
        
        for week in range(9, 13):
            for sid in sids:
                for course in COURSES:
                    aid = generate_uuid()
                    phase3_activity_ids.append(aid)
                    
                    if sid in recovering_sids:
                        score = random.randint(85, 98) # RECOVERY in all subjects
                    elif sid in dropping_config and sid in still_at_risk_sids and course["id"] in dropping_config[sid]:
                        score = random.randint(15, 35) # PERSISTENT in dropped subjects
                    else:
                        score = random.randint(80, 95)
                    
                    session.add(Activity(
                        activity_id=aid,
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

        # Resolve Cases for recovered students
        for sid in recovering_sids:
            stmt = select(Case).where(Case.sid == sid, Case.intervention_status != InterventionStatus.RESOLVED)
            case = (await session.execute(stmt)).scalar_one_or_none()
            if case:
                case.intervention_status = InterventionStatus.RESOLVED
                case.closed_at = START_DATE + timedelta(weeks=12, days=1)
                session.add(PointLedger(
                    id=generate_uuid(),
                    advisor_id=ADVISOR_ID,
                    case_id=case.case_id,
                    action="resolve_case",
                    points=50,
                    earned_at=case.closed_at
                ))
        
        await session.commit()
        await run_anomaly_detection(session)
        await export_phase_csv(session, 3, phase3_activity_ids)
        print("Phase 3 Complete.")

        print("\nSummary:")
        print("- Total Students: 20")
        print("- Subjects: Programming, Calculus, Literature, Psychology")
        print("- Systemic Breadth Examples:")
        print("  * Student B: 3 subjects drop (Breadth: 0.75)")
        print("  * Student E: 4 subjects drop (Breadth: 1.00)")
        print("- Expected Recovery Rate: 60.0%")

if __name__ == "__main__":
    asyncio.run(generate_3_phases())
