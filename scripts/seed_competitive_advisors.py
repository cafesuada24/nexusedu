"""
Script to generate competitive advisor data directly in the database.
Creates multiple advisors with different performance profiles (XP, recovery rate, response time).
"""

import asyncio
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

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
    Advisor,
    Case,
    PointLedger,
    Student,
    User,
)
from src.infrastructure.database.session import async_session_maker
from src.presentation.api.auth import UserRole
from fastapi_users.password import PasswordHelper

password_helper = PasswordHelper()
from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
    SqlAlchemyUserSettingsRepository,
)

# Advisor Performance Profiles
ADVISOR_PROFILES = [
    {
        "name": "Alex Top-Performer",
        "email": "alex@example.com",
        "title": "Senior Interventionist",
        "xp_boost": 2500,
        "recovery_target": 0.85,
        "response_hours": 1.5
    },
    {
        "name": "Jordan Consistent",
        "email": "jordan@example.com",
        "title": "Academic Advisor",
        "xp_boost": 1800,
        "recovery_target": 0.70,
        "response_hours": 3.2
    },
    {
        "name": "Taylor Newcomer",
        "email": "taylor@example.com",
        "title": "Junior Advisor",
        "xp_boost": 600,
        "recovery_target": 0.45,
        "response_hours": 8.5
    },
    {
        "name": "Morgan Specialist",
        "email": "morgan@example.com",
        "title": "Lead Specialist",
        "xp_boost": 2100,
        "recovery_target": 0.80,
        "response_hours": 2.1
    }
]

async def seed_competitive_data():
    print("Seeding competitive advisor data...")
    async with async_session_maker() as session:
        settings_repo = SqlAlchemyUserSettingsRepository(session)
        
        # 1. Get some existing students to assign cases to
        stmt_students = select(Student).limit(40)
        students = (await session.execute(stmt_students)).scalars().all()
        
        if not students:
            print("Error: No students found in database. Run generate_3_phase_datasets.py first.")
            return

        now = datetime.now(UTC)

        for profile in ADVISOR_PROFILES:
            # Check if user exists
            stmt_user = select(User).where(User.email == profile["email"])
            user = (await session.execute(stmt_user)).scalar_one_or_none()
            
            if not user:
                user_id = generate_uuid()
                user = User(
                    id=user_id,
                    email=profile["email"],
                    hashed_password=password_helper.hash("password"),
                    is_active=True,
                    is_verified=True,
                    role=UserRole.ADVISOR.value
                )
                session.add(user)
                await session.flush()
                await settings_repo.create_user_settings(user_id)
            else:
                user_id = user.id

            # Check if advisor exists
            stmt_adv = select(Advisor).where(Advisor.email == profile["email"])
            advisor = (await session.execute(stmt_adv)).scalar_one_or_none()
            
            if not advisor:
                advisor_id = generate_uuid()
                advisor = Advisor(
                    advisor_id=advisor_id,
                    name=profile["name"],
                    email=profile["email"],
                    title=profile["title"],
                    user_id=user_id
                )
                session.add(advisor)
                await session.flush()
            else:
                advisor_id = advisor.advisor_id

            print(f"Generating performance data for {profile['name']}...")

            # 2. Generate Cases and Points for the advisor
            # We want to create a history of points to show Impact XP
            num_cases = random.randint(10, 20)
            assigned_students = random.sample(students, min(num_cases, len(students)))

            for i, student in enumerate(assigned_students):
                created_at = now - timedelta(days=random.randint(5, 30))
                
                # Determine if this case is resolved (based on recovery target)
                is_resolved = random.random() < profile["recovery_target"]
                status = InterventionStatus.RESOLVED if is_resolved else InterventionStatus.SUPPORTING
                
                case_id = generate_uuid()
                case = Case(
                    case_id=case_id,
                    sid=student.sid,
                    risk_reason=RiskReason.GRADE_DROP,
                    intervention_status=status,
                    created_at=created_at,
                    assigned_advisor_id=advisor_id,
                    closed_at=created_at + timedelta(days=random.randint(3, 10)) if is_resolved else None,
                    version=1
                )
                session.add(case)
                
                # Add Response KPI points (First Response)
                response_delay = timedelta(hours=profile["response_hours"] * random.uniform(0.8, 1.2))
                resp_at = created_at + response_delay
                session.add(PointLedger(
                    id=generate_uuid(),
                    advisor_id=advisor_id,
                    case_id=case_id,
                    action="first_response",
                    points=10,
                    earned_at=resp_at
                ))

                # Add some more activity points
                session.add(PointLedger(
                    id=generate_uuid(),
                    advisor_id=advisor_id,
                    case_id=case_id,
                    action="send_nudge",
                    points=15,
                    earned_at=resp_at + timedelta(minutes=30)
                ))

                if is_resolved:
                    session.add(PointLedger(
                        id=generate_uuid(),
                        advisor_id=advisor_id,
                        case_id=case_id,
                        action="resolve_case",
                        points=50,
                        earned_at=case.closed_at
                    ))

            # 3. Add bulk "Legacy" XP to differentiate the leaderboard significantly
            # We assign these to the LAST case generated for this advisor to satisfy NOT NULL constraint
            if assigned_students:
                last_case_id = case_id
                for week_offset in range(4):
                    session.add(PointLedger(
                        id=generate_uuid(),
                        advisor_id=advisor_id,
                        case_id=last_case_id,
                        action="historical_impact",
                        points=profile["xp_boost"] // 4,
                        earned_at=now - timedelta(weeks=week_offset)
                    ))

        await session.commit()
        print("\nSuccess: Competitive advisor data seeded.")
        print("Advisors created: Alex, Jordan, Taylor, Morgan.")
        print("Check the Admin Dashboard leaderboard and comparison charts.")

if __name__ == "__main__":
    asyncio.run(seed_competitive_data())
