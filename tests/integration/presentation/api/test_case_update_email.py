"""Integration tests for manual email update endpoint."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from src.domain.entities.case import Case
from src.domain.entities.intervention_email import InterventionEmail
from src.domain.value_objects.status import EmailStatus, InterventionStatus
from src.infrastructure.database.models import Advisor
from src.presentation.api.auth import UserRole

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.domain.repositories.case_repository import CaseRepository
    from src.domain.repositories.email_repository import EmailRepository
    from src.domain.repositories.student_repository import StudentRepository
    from src.presentation.api.auth import User


@pytest.fixture
async def seed_data(
    test_db_session: AsyncSession,
    mock_user: User,
    case_repository: CaseRepository,
    student_repository: StudentRepository,
    email_repository: EmailRepository,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Seed an advisor, student, case, and email draft."""
    mock_user.role = UserRole.ADVISOR.value
    advisor_id = uuid.uuid4()
    sid = uuid.uuid4()
    cid = uuid.uuid4()
    eid = uuid.uuid4()

    # 1. Seed Advisor
    test_db_session.add(
        Advisor(
            advisor_id=advisor_id,
            user_id=mock_user.id,
            name='Test Advisor',
            email=mock_user.email,
        ),
    )

    # 2. Seed Student
    await student_repository.ingest_students(
        [{'sid': sid, 'student_name': 'Test Student', 'email': 'student@example.com'}],
    )

    # 3. Seed Case assigned to this advisor
    case = Case(case_id=cid, sid=sid)
    case.assign_advisor(advisor_id, occurred_at=datetime.now(UTC))
    await case_repository.add(case)

    # 4. Seed Email Draft
    email = InterventionEmail(case_id=cid, email_id=eid)
    email.mark_as_generating()
    email.set_draft_content("Original Subject", "Original Body")
    await email_repository.add(email)

    await test_db_session.commit()
    return advisor_id, sid, cid


@pytest.mark.asyncio
async def test_update_email_draft_success(
    client: TestClient,
    seed_data: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """Verify advisor can successfully update a draft email."""
    _, _, cid = seed_data

    payload = {
        "subject": "Updated Subject",
        "body": "Updated Body",
    }

    response = client.patch(f"/api/v1/cases/{cid}/email", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Draft updated"}

    # Verify persistence
    get_resp = client.get(f"/api/v1/cases/{cid}/email")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["subject"] == "Updated Subject"
    assert data["body"] == "Updated Body"


@pytest.mark.asyncio
async def test_update_email_draft_partial(
    client: TestClient,
    seed_data: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """Verify advisor can partially update a draft email (body only)."""
    _, _, cid = seed_data

    payload = {
        "body": "Only body updated",
    }

    response = client.patch(f"/api/v1/cases/{cid}/email", json=payload)

    assert response.status_code == 200

    get_resp = client.get(f"/api/v1/cases/{cid}/email")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["subject"] == "Original Subject" # Should remain same
    assert data["body"] == "Only body updated"


@pytest.mark.asyncio
async def test_update_email_draft_unauthorized_advisor(
    client: TestClient,
    mock_user: User,
    test_db_session: AsyncSession,
    case_repository: CaseRepository,
    student_repository: StudentRepository,
    email_repository: EmailRepository,
) -> None:
    """Verify an advisor cannot update an email for a case they don't own."""
    # 1. Seed Advisor for mock_user so we pass the "is advisor" check
    mock_user.role = UserRole.ADVISOR.value
    test_db_session.add(
        Advisor(
            advisor_id=uuid.uuid4(),
            user_id=mock_user.id,
            name='Test Advisor',
            email=mock_user.email,
        ),
    )

    # 2. Seed a case assigned to a DIFFERENT advisor
    other_advisor_id = uuid.uuid4()
    sid = uuid.uuid4()
    cid = uuid.uuid4()

    await student_repository.ingest_students(
        [{'sid': sid, 'student_name': 'Other Student', 'email': 'other@example.com'}],
    )
    case = Case(case_id=cid, sid=sid)
    # Manually set assigned_advisor_id instead of assign_advisor to avoid side effects if needed,
    # but assign_advisor is fine too.
    case.assigned_advisor_id = other_advisor_id
    case.intervention_status = InterventionStatus.ACCEPTED
    await case_repository.add(case)

    email = InterventionEmail(case_id=cid)
    email.mark_as_generating()
    email.set_draft_content("S", "B")
    await email_repository.add(email)

    await test_db_session.commit()

    payload = {"body": "Try to hack"}
    response = client.patch(f"/api/v1/cases/{cid}/email", json=payload)

    # Should fail with 404 because handler checks ownership and raises CaseNotFoundError
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_email_draft_invalid_state(
    client: TestClient,
    seed_data: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
    email_repository: EmailRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify advisor cannot update an email that is already SENT."""
    _, _, cid = seed_data

    # Transition email to SENT
    email = await email_repository.find_by_case(cid)
    email.mark_as_sent()
    await email_repository.save(email)
    await test_db_session.commit()

    payload = {"body": "Update sent email"}
    response = client.patch(f"/api/v1/cases/{cid}/email", json=payload)

    assert response.status_code == 400
    assert "email is sent" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_email_created_on_accept(
    client: TestClient,
    test_db_session: AsyncSession,
    case_repository: CaseRepository,
    student_repository: StudentRepository,
    email_repository: EmailRepository,
    mock_user: User,
) -> None:
    """Verify that an InterventionEmail is created immediately when a case is accepted."""
    mock_user.role = UserRole.ADVISOR.value
    # 1. Seed Advisor
    test_db_session.add(
        Advisor(
            advisor_id=uuid.uuid4(),
            user_id=mock_user.id,
            name='Test Advisor',
            email=mock_user.email,
        ),
    )

    # 2. Seed Student and NEW Case
    sid = uuid.uuid4()
    cid = uuid.uuid4()
    await student_repository.ingest_students(
        [{'sid': sid, 'student_name': 'New Student', 'email': 'new@example.com'}],
    )
    case = Case(case_id=cid, sid=sid)
    await case_repository.add(case)
    await test_db_session.commit()

    # 3. Verify no email exists yet
    email_before = await email_repository.find_by_case(cid)
    assert email_before is None

    # 4. Accept Case via API
    response = client.post(f"/api/v1/cases/{cid}/accept")
    assert response.status_code == 200

    # 5. Verify email record was created
    email_after = await email_repository.find_by_case(cid)
    assert email_after is not None
    assert email_after.case_id == cid
    assert email_after.status == EmailStatus.UNAVAILABLE
