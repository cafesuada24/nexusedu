"""Integration tests for the book appointment endpoint."""

import uuid
import pytest
from typing import TYPE_CHECKING
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.case import Case
from src.domain.value_objects.status import InterventionStatus
from src.infrastructure.database.models import Advisor, User

if TYPE_CHECKING:
    from src.domain.repositories.case_repository import CaseRepository
    from src.domain.repositories.student_repository import StudentRepository
    from src.domain.repositories.email_repository import EmailRepository

@pytest.fixture(autouse=True)
async def seed_advisor(test_db_session: AsyncSession, mock_user: User) -> None:
    """Seed an advisor profile for the mock user."""
    from uuid import uuid4
    from src.presentation.api.auth import User
    
    test_db_session.add(
        Advisor(
            advisor_id=uuid4(),
            user_id=mock_user.id,
            name='Test Advisor',
            email=mock_user.email,
        )
    )
    await test_db_session.commit()

@pytest.mark.asyncio
async def test_book_appointment_success(
    client: TestClient,
    case_repository: "CaseRepository",
    student_repository: "StudentRepository",
    email_repository: "EmailRepository",
) -> None:
    """Verify that a student can book an appointment when the case is in SENT status."""
    sid = uuid.uuid4()
    cid = uuid.uuid4()
    
    # 1. Setup: Create student and case in SENT status
    await student_repository.ingest_students(
        [
            {
                'sid': sid,
                'student_name': 'Booking Student',
                'email': 'student@example.com',
            },
        ]
    )
    
    case = Case(case_id=cid, sid=sid)
    # Manually transition to SENT for testing
    case.intervention_status = InterventionStatus.ACCEPTED
    case.mark_as_sent()
    
    await case_repository.add(case)
    await student_repository.session.commit()

    # 2. Act: Call the book endpoint
    response = client.post(f'/api/v1/cases/{cid}/book')

    # 3. Assert
    assert response.status_code == 200
    assert response.json() == {'status': 'success', 'message': 'Appointment booked successfully'}
    
    # Verify status changed in DB
    updated_case = await case_repository.get_by_id(cid)
    assert updated_case.intervention_status == InterventionStatus.BOOKED

@pytest.mark.asyncio
async def test_book_appointment_case_not_found(client: TestClient) -> None:
    """Verify 404 is returned for a non-existent case."""
    random_id = uuid.uuid4()
    response = client.post(f'/api/v1/cases/{random_id}/book')
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_book_appointment_invalid_transition(
    client: TestClient,
    case_repository: "CaseRepository",
    student_repository: "StudentRepository",
) -> None:
    """Verify 400 is returned when case is not in SENT status (e.g., NEW)."""
    sid = uuid.uuid4()
    cid = uuid.uuid4()
    
    # Setup: Create case in NEW status
    await student_repository.ingest_students(
        [{'sid': sid, 'student_name': 'New Student', 'email': 'new@example.com'}]
    )
    case = Case(case_id=cid, sid=sid) # Default status is NEW
    await case_repository.add(case)
    await student_repository.session.commit()

    # Act: Call the book endpoint
    response = client.post(f'/api/v1/cases/{cid}/book')

    # Assert
    assert response.status_code == 400
    assert 'Cannot transite to booked' in response.json()['detail']
