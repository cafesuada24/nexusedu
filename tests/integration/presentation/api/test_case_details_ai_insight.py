import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient

from src.domain.entities.case import Case
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.student_repository import StudentRepository
from src.infrastructure.database.models import Advisor
from src.presentation.api.auth import User


@pytest.fixture(autouse=True)
async def seed_advisor(test_db_session: AsyncSession, mock_user: User) -> None:
    """Seed an advisor profile for the mock user."""
    test_db_session.add(
        Advisor(
            advisor_id=uuid.uuid4(),
            user_id=mock_user.id,
            name='Test Advisor',
            email=mock_user.email,
        ),
    )
    await test_db_session.commit()


@pytest.mark.asyncio
async def test_get_case_details_with_ai_insight(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that the case details endpoint returns ai_overview."""
    sid = uuid.uuid4()
    cid = uuid.uuid4()

    # 1. Ingest a student
    await student_repository.ingest_students(
        [
            {
                'sid': sid,
                'student_name': 'AI Test Student',
                'email': 'ai@test.com',
                'current_risk_status': 'Critical',
                'major': 'CS',
            },
        ],
    )

    # 2. Create a case with AI overview
    case = Case(
        case_id=cid, 
        sid=sid,
        academic_summary="This student is doing great but needs more sleep.",
        action_keys=["Sleep", "Rest", "Eat"]
    )
    await case_repository.add(case)

    # 3. Fetch case details
    response = client.get(f'/api/v1/cases/{cid}')
    assert response.status_code == 200

    data = response.json()
    assert data['case_id'] == str(cid)
    assert 'ai_overview' in data
    assert data['ai_overview'] is not None
    assert data['ai_overview']['academic_summary'] == "This student is doing great but needs more sleep."
    assert data['ai_overview']['action_keys'] == ["Sleep", "Rest", "Eat"]


@pytest.mark.asyncio
async def test_get_case_details_without_ai_insight(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
) -> None:
    """Verify that ai_overview is None when not present."""
    sid = uuid.uuid4()
    cid = uuid.uuid4()

    # 1. Ingest a student
    await student_repository.ingest_students(
        [
            {
                'sid': sid,
                'student_name': 'No AI Student',
                'email': 'noai@test.com',
                'current_risk_status': 'Normal',
                'major': 'Math',
            },
        ],
    )

    # 2. Create a case without AI overview
    case = Case(case_id=cid, sid=sid)
    await case_repository.add(case)

    # 3. Fetch case details
    response = client.get(f'/api/v1/cases/{cid}')
    assert response.status_code == 200

    data = response.json()
    assert data['case_id'] == str(cid)
    assert data['ai_overview'] is None
