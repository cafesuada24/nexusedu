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
from src.infrastructure.database.models import Activity, Case, Student  # noqa: E402
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
                    score=random.randint(75, 90),
                    timestamp=start_date + timedelta(weeks=week-5),
                    academic_year=2026,
                    semester=1,
                    week=week,
                ))

        # 4. Trigger Risk Change
        student_a.current_risk_status = RiskStatus.CRITICAL

        # 5. Create NEW Case for Student A
        new_case = Case(
            case_id=generate_uuid(),
            sid=student_a.sid,
            risk_reason=RiskReason.GRADE_DROP,
            intervention_status=InterventionStatus.NEW,
            created_at=datetime.now(UTC),
            version=1,
        )
        session.add(new_case)

        await session.commit()
        print(f"\nStudent A ({student_a.sid}) is now CRITICAL.")
        print(f"New Case created: {new_case.case_id}")
        print("\nNEXT STEP: Open the Advisor UI, Accept the case, and Send a Nudge.")

if __name__ == '__main__':
    asyncio.run(simulate_drop())
