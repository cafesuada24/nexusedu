"""Step 1: Simulate a performance drop for Student A and trigger risk alerts."""

import asyncio
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.identifiers import generate_uuid  # noqa: E402
from src.domain.value_objects.status import (  # noqa: E402
    InterventionStatus,
    RiskReason,
    RiskStatus,
)
from src.infrastructure.database.models import Activity, Advisor, Case, Student  # noqa: E402
from src.infrastructure.database.session import async_session_maker  # noqa: E402


async def simulate_drop() -> None:
    """Add low scores for Student A and create a critical case."""
    print("Simulating performance drop for Weeks 5-8...")

    async with async_session_maker() as session:
        # 1. Find Student A
        stmt = select(Student).where(Student.student_name == 'Student A')
        student_a = (await session.execute(stmt)).scalar_one()

        # 2. Add dropping scores for Student A (Weeks 5-8)
        start_date = datetime(2026, 2, 2, tzinfo=UTC) # February
        for week in range(5, 9):
            session.add(Activity(
                activity_id=generate_uuid(),
                sid=student_a.sid,
                course_id='CS101',
                course_name='Intro Course',
                test_type='Quiz',
                score=random.randint(15, 35), # CRASH
                timestamp=start_date + timedelta(weeks=week-5),
                academic_year=2026,
                semester=1,
                week=week,
            ))

        # 3. Add normal scores for others to show contrast
        stmt_others = select(Student).where(Student.sid != student_a.sid)
        others = (await session.execute(stmt_others)).scalars().all()
        for student in others:
            for week in range(5, 9):
                session.add(Activity(
                    activity_id=generate_uuid(),
                    sid=student.sid,
                    course_id='CS101',
                    course_name='Intro Course',
                    test_type='Quiz',
                    score=random.randint(80, 95),
                    timestamp=start_date + timedelta(weeks=week-5),
                    academic_year=2026,
                    semester=1,
                    week=week,
                ))

        # 4. Run Anomaly Detection to update statuses
        print("Running anomaly detection...")
        from collections import defaultdict
        from src.domain.services.anomaly_engine.zscore import ZScore
        from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
            SqlAlchemyActivityRepository,
            SqlAlchemyStatusHistoryRepository,
            SqlAlchemyStudentRepository,
            SqlAlchemyAdvisorRepository,
        )

        student_repo = SqlAlchemyStudentRepository(session)
        activity_repo = SqlAlchemyActivityRepository(session)
        history_repo = SqlAlchemyStatusHistoryRepository(session)
        advisor_repo = SqlAlchemyAdvisorRepository(session)

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

        # Apply transitions and identify new at-risk
        new_at_risk_sids = []
        for sid, latest_risk in risk_statuses.items():
            if latest_risk == RiskStatus.NORMAL:
                continue
            
            student = await student_repo.get_by_id(sid)
            if student.current_risk_status == RiskStatus.NORMAL:
                student.current_risk_status = latest_risk
                await student_repo.save(student)
                new_at_risk_sids.append(sid)

        # 5. Create NEW Case for new at-risk students
        
        for sid in new_at_risk_sids:
            case_id = generate_uuid()
            new_case = Case(
                case_id=case_id,
                sid=sid,
                risk_reason=RiskReason.GRADE_DROP,
                intervention_status=InterventionStatus.NEW,
                created_at=datetime.now(UTC),
                version=1,
            )
            session.add(new_case)
            print(f"New Case created for {sid}: {case_id} (Status: {risk_statuses[sid]})")

        await session.commit()
        print("\nDrop simulation complete.")
        print("NEXT STEP: Open the Advisor UI, Accept the case, and Send a Nudge.")

if __name__ == '__main__':
    asyncio.run(simulate_drop())
