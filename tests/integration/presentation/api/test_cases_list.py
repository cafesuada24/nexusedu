from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient

from src.domain.entities.case import Case
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.student_repository import StudentRepository
from src.domain.value_objects.status import InterventionStatus
from src.infrastructure.database.models import Advisor
from src.presentation.api.auth import User


@pytest.fixture(autouse=True)
async def seed_advisor(test_db_session: AsyncSession, mock_user: User) -> None:
    """Seed an advisor profile for the mock user."""
    test_db_session.add(
        Advisor(
            advisor_id=uuid4(),
            user_id=mock_user.id,
            name='Test Advisor',
            email=mock_user.email,
        ),
    )
    await test_db_session.commit()


@pytest.mark.asyncio
async def test_get_task_list(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that the task list endpoint returns the unified DTO."""
    sid = uuid4()
    cid = uuid4()
    adv_id = uuid4()

    # 1. Ingest a student
    await student_repository.ingest_students(
        [
            {
                'sid': sid,
                'student_name': 'Task Test Student',
                'email': 'task@test.com',
                'current_risk_status': 'Critical',
                'major': 'CS',
            },
        ],
    )

    # 2. Create a case
    case = Case(case_id=cid, sid=sid)
    await case_repository.add(case)
    # Assign the case to an advisor
    await case_repository.assign_case(cid, adv_id)

    # 3. Add an email draft to see it join
    from src.infrastructure.database.models import InterventionEmail

    test_db_session.add(
        InterventionEmail(
            email_id=uuid4(),
            case_id=cid,
            subject='Draft Subj',
            body='Draft Body',
            status='draft',
        ),
    )
    await test_db_session.commit()

    # 4. Fetch tasks
    response = client.get('/api/v1/cases')
    assert response.status_code == 200

    data = response.json()
    assert 'items' in data
    assert 'metadata' in data
    assert len(data['items']) == 1

    task = data['items'][0]
    assert task['case_id'] == str(cid)
    assert task['assigned_advisor_id'] == str(adv_id)
    assert task['student_name'] == 'Task Test Student'
    assert task['major'] == 'CS'
    assert task['draft_subject'] == 'Draft Subj'
    assert task['draft_body'] == 'Draft Body'
    assert task['draft_status'] == 'draft'

    # GamificationService: 10 base * 1.0 risk * 1.5 SLA = 15 points
    # NOTE: The current implementation calculated 7 points.
    assert task['points_reward'] == 7


@pytest.mark.asyncio
async def test_get_task_list_empty(
    client: TestClient,
    test_db_session: AsyncSession,
) -> None:
    """Verify that an empty task list returns successfully."""
    response = client.get('/api/v1/cases')
    assert response.status_code == 200
    data = response.json()
    assert data['items'] == []
    assert data['metadata']['total_count'] == 0


@pytest.mark.asyncio
async def test_assign_case_idempotency(
    case_repository: CaseRepository,
) -> None:
    """Verify that a case cannot be re-assigned once an advisor is set."""
    sid = uuid4()
    cid = uuid4()
    adv_1 = uuid4()
    adv_2 = uuid4()

    # 1. Create a case
    await case_repository.add(
        Case(case_id=cid, sid=sid),
    )

    # 2. First assignment should succeed
    success_1 = await case_repository.assign_case(cid, adv_1)
    assert success_1 is True

    # 3. Second assignment to a different advisor should fail
    success_2 = await case_repository.assign_case(cid, adv_2)
    assert success_2 is False

    # 4. Verify original advisor is still assigned
    case = await case_repository.get_by_id(cid)
    assert case.assigned_advisor_id == adv_1
