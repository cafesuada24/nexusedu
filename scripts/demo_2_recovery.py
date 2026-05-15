"""Step 2: Simulate recovery for Student A and demonstrate intervention ROI."""

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
from src.domain.value_objects.status import RiskStatus  # noqa: E402
from src.infrastructure.database.models import Activity, Student  # noqa: E402
from src.infrastructure.database.session import async_session_maker  # noqa: E402


async def simulate_recovery() -> None:
    """Add high scores for Student A and update status to Normal."""
    print("Simulating recovery for Weeks 9-12...")

    async with async_session_maker() as session:
        # 1. Find Student A
        stmt = select(Student).where(Student.student_name == 'Student A')
        student_a = (await session.execute(stmt)).scalar_one()

        # 2. Add recovery scores for Student A (Weeks 9-12)
        start_date = datetime(2026, 3, 2, tzinfo=UTC) # March
        for week in range(9, 13):
            session.add(Activity(
                activity_id=generate_uuid(),
                sid=student_a.sid,
                course_id='CS101',
                course_name='Intro Course',
                test_type='Quiz',
                score=random.randint(85, 98), # RECOVERY
                timestamp=start_date + timedelta(weeks=week-9),
                academic_year=2026,
                semester=1,
                week=week,
            ))

        # 3. Add normal scores for others
        stmt_others = select(Student).where(Student.sid != student_a.sid)
        others = (await session.execute(stmt_others)).scalars().all()
        for student in others:
            for week in range(9, 13):
                session.add(Activity(
                    activity_id=generate_uuid(),
                    sid=student.sid,
                    course_id='CS101',
                    course_name='Intro Course',
                    test_type='Quiz',
                    score=random.randint(80, 95),
                    timestamp=start_date + timedelta(weeks=week-9),
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
        )

        student_repo = SqlAlchemyStudentRepository(session)
        activity_repo = SqlAlchemyActivityRepository(session)
        history_repo = SqlAlchemyStatusHistoryRepository(session)

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
        
        print(f"Detected risk statuses for {len(risk_statuses)} students.")
        target_status = risk_statuses.get(student_a.sid)
        print(f"Student A ({student_a.sid}) latest risk status: {target_status}")

        if new_history_records:
            await history_repo.batch_create_history(new_history_records)

        # Apply transitions
        for sid, latest_risk in risk_statuses.items():
            if latest_risk == RiskStatus.NORMAL:
                student = await student_repo.get_by_id(sid)
                if student.current_risk_status != RiskStatus.NORMAL:
                    student.current_risk_status = RiskStatus.NORMAL
                    await student_repo.save(student)
                    print(f"Student {sid} has recovered and is now NORMAL.")

        await session.commit()
        print("\nRecovery simulation complete.")
        print("\nNEXT STEP: Open the Advisor UI and Resolve the case for Student A.")
        print("Then, check the Admin Dashboard to see 'Recovery Rate' and 'Academic Impact Score'.")

if __name__ == '__main__':
    asyncio.run(simulate_recovery())
