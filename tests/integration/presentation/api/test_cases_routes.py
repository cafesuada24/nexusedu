"""Integration tests for Student Case routes."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from src.domain.entities.case import Case
from src.domain.value_objects.status import EmailStatus, InterventionStatus
from src.infrastructure.database.models import Advisor

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.presentation.api.auth import User

    from src.domain.repositories.case_repository import CaseRepository
...
@pytest.fixture(autouse=True)
async def seed_advisor(test_db_session: AsyncSession, mock_user: User) -> None:
    """Seed an advisor profile for the mock user."""
    from uuid import uuid4
    test_db_session.add(
        Advisor(
            advisor_id=uuid4(),
            user_id=mock_user.id,
            name='Test Advisor',
            email=mock_user.email,
        )
    )
    await test_db_session.commit()
    from src.domain.repositories.email_repository import EmailRepository
    from src.domain.repositories.student_repository import StudentRepository


@pytest.mark.asyncio
async def test_update_case_status(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
) -> None:
    """Verify that status updates work correctly via case_id."""
    sid = uuid.uuid4()
    cid = uuid.uuid4()
    await student_repository.ingest_students(
        [
            {
                'sid': sid,
                'student_name': 'P',
                'email': 'p@ex.com',
                'intervention_status': InterventionStatus.NOTIFIED.value,
            },
        ]
    )
    await case_repository.create_case(Case(case_id=cid, sid=sid))
    await student_repository.session.commit()

    response = client.patch(f'/api/v1/cases/{cid}/status', json={'status': 'booked'})
    assert response.status_code == 200

    student = await student_repository.get_by_id(sid)
    assert student.intervention_status == InterventionStatus.BOOKED


@pytest.mark.asyncio
async def test_trigger_draft(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
) -> None:
    """Verify manual draft triggering via case_id."""
    sid = uuid.uuid4()
    cid = uuid.uuid4()
    await student_repository.ingest_students(
        [
            {
                'sid': sid,
                'student_name': 'T',
                'email': 't@ex.com',
                'intervention_status': InterventionStatus.NOTIFIED.value,
            },
        ]
    )
    await case_repository.create_case(Case(case_id=cid, sid=sid))
    await student_repository.session.commit()

    response = client.post(f'/api/v1/cases/{cid}/email/draft', json={})
    assert response.status_code == 202
    assert 'job_id' in response.json()


@pytest.mark.asyncio
async def test_review_draft_idempotency(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
) -> None:
    """Verify points awarding for draft review via case_id."""
    sid = uuid.uuid4()
    cid = uuid.uuid4()
    await student_repository.ingest_students(
        [{'sid': sid, 'student_name': 'R', 'email': 'r@ex.com'}]
    )
    await case_repository.create_case(Case(case_id=cid, sid=sid))
    await student_repository.session.commit()

    key = str(uuid.uuid4())
    headers = {'Idempotency-Key': key}

    # 1. First review
    resp1 = client.post(f'/api/v1/cases/{cid}/email/draft/review', headers=headers)
    assert resp1.status_code == 200
    assert 'awarded' in resp1.json()['message']


@pytest.mark.asyncio
async def test_send_email_flow(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
    email_repository: EmailRepository,
) -> None:
    """Verify the full email sending flow via case_id."""
    sid = uuid.uuid4()
    cid = uuid.uuid4()
    await student_repository.ingest_students(
        [
            {
                'sid': sid,
                'student_name': 'S',
                'email': 's@ex.com',
                'intervention_status': InterventionStatus.NOTIFIED.value,
            },
        ],
    )
    await case_repository.create_case(Case(case_id=cid, sid=sid))
    await email_repository.create_placeholder(cid, sid, uuid.uuid4())
    await email_repository.update_content(cid, 'Subject', 'Body', EmailStatus.DRAFT)
    await student_repository.session.commit()

    headers = {'Idempotency-Key': str(uuid.uuid4())}
    response = client.post(f'/api/v1/cases/{cid}/email/send', json={'body': 'Sent body'}, headers=headers)
    assert response.status_code == 200

    # Check status
    student = await student_repository.get_by_id(sid)
    assert student.intervention_status == InterventionStatus.SENT

    # Check history
    history = client.get(f'/api/v1/cases/{cid}/email')
    hist = history.json()
    assert hist['status'] == 'sent'


@pytest.mark.asyncio
async def test_get_email_draft(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
    email_repository: EmailRepository,
) -> None:
    """Verify retrieving the current draft content via case_id."""
    sid = uuid.uuid4()
    cid = uuid.uuid4()
    await student_repository.ingest_students(
        [{'sid': sid, 'student_name': 'D', 'email': 'd@ex.com'}]
    )
    await case_repository.create_case(Case(case_id=cid, sid=sid))
    await email_repository.create_placeholder(cid, sid, uuid.uuid4())
    await email_repository.update_content(cid, 'Draft Sub', 'Draft Body', EmailStatus.DRAFT)
    await student_repository.session.commit()

    response = client.get(f'/api/v1/cases/{cid}/email/draft')
    assert response.status_code == 200
    data = response.json()
    assert data['subject'] == 'Draft Sub'
    assert data['body'] == 'Draft Body'
    assert data['is_generating'] is False


@pytest.mark.asyncio
async def test_get_case_history(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
) -> None:
    """Verify retrieving historical cases for a student."""
    sid = uuid.uuid4()
    cid = uuid.uuid4()
    await student_repository.ingest_students(
        [{'sid': sid, 'student_name': 'H', 'email': 'h@ex.com'}]
    )
    await case_repository.create_case(Case(case_id=cid, sid=sid))
    await student_repository.session.commit()

    response = client.get(f'/api/v1/cases/student/{sid}')
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['case_id'] == str(cid)
