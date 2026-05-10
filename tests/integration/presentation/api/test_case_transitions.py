"""Integration tests for the book appointment endpoint."""

import uuid
from datetime import UTC, datetime
import pytest
from typing import TYPE_CHECKING
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.case import Case
from src.domain.value_objects.status import InterventionStatus, MeetingMethod
from src.infrastructure.database.models import Advisor, AdvisorWorkingHours, User

@pytest.fixture(autouse=True)
async def seed_advisor(test_db_session: AsyncSession, mock_user: User) -> None:
    """Seed an advisor profile and working hours for the mock user."""
    from datetime import time
    from uuid import uuid4
    
    advisor_id = uuid4()
    test_db_session.add(
        Advisor(
            advisor_id=advisor_id,
            user_id=mock_user.id,
            name='Test Advisor',
            email=mock_user.email,
        )
    )
    # Seed working hours for Monday (day 0) 9-5 UTC
    test_db_session.add(
        AdvisorWorkingHours(
            advisor_id=advisor_id,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(17, 0),
            timezone='UTC',
        )
    )
    await test_db_session.commit()

@pytest.mark.asyncio
async def test_book_appointment_success(
    client: TestClient,
    case_repository: "CaseRepository",
    student_repository: "StudentRepository",
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

    # 2. Act: Call the book endpoint with a valid future Monday slot
    # 2026-05-11 is a Monday
    payload = {
        'appointment_time': '2026-05-11T10:00:00Z',
        'meeting_method': 'online',
        'notes': 'Test booking',
    }
    response = client.post(f'/api/v1/cases/{cid}/book', json=payload)

    # 3. Assert
    assert response.status_code == 200
    assert response.json() == {
        'status': 'success',
        'message': 'Appointment booked successfully',
    }

    # Verify status changed in DB
    updated_case = await case_repository.get_by_id(cid)
    assert updated_case.intervention_status == InterventionStatus.BOOKED


@pytest.mark.asyncio
async def test_start_supporting_success(
    client: TestClient,
    case_repository: "CaseRepository",
    student_repository: "StudentRepository",
    mock_user: User,
    test_db_session: AsyncSession,
) -> None:
    """Verify that an advisor can start supporting a student after booking."""
    sid = uuid.uuid4()
    cid = uuid.uuid4()

    # Setup: Create student and case in BOOKED status
    await student_repository.ingest_students(
        [{'sid': sid, 'student_name': 'S', 'email': 's@ex.com'}]
    )

    # Get the advisor seeded in fixture
    from sqlalchemy import select
    from src.infrastructure.database.models import Advisor

    result = await test_db_session.execute(
        select(Advisor).where(Advisor.user_id == mock_user.id)
    )
    advisor = result.scalar_one()

    case = Case(case_id=cid, sid=sid)
    # Manually setup the case as booked and assigned to the mock advisor
    case.intervention_status = InterventionStatus.ACCEPTED
    case.assigned_advisor_id = advisor.advisor_id
    case.mark_as_sent()
    case.record_booking(
        appointment_time=datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
        meeting_method=MeetingMethod.ONLINE,
    )

    await case_repository.add(case)
    await student_repository.session.commit()

    # Act: Call the supporting endpoint
    response = client.post(f'/api/v1/cases/{cid}/supporting')

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        'status': 'success',
        'message': 'Support session started successfully',
    }

    # Verify status changed in DB
    updated_case = await case_repository.get_by_id(cid)
    assert updated_case.intervention_status == InterventionStatus.SUPPORTING


@pytest.mark.asyncio
async def test_resolve_case_success(
    client: TestClient,
    case_repository: "CaseRepository",
    student_repository: "StudentRepository",
    mock_user: User,
    test_db_session: AsyncSession,
) -> None:
    """Verify that an advisor can resolve a student case."""
    sid = uuid.uuid4()
    cid = uuid.uuid4()

    # Setup: Create student and case in SUPPORTING status
    await student_repository.ingest_students(
        [{'sid': sid, 'student_name': 'R', 'email': 'r@ex.com'}]
    )

    from sqlalchemy import select
    from src.infrastructure.database.models import Advisor

    result = await test_db_session.execute(
        select(Advisor).where(Advisor.user_id == mock_user.id)
    )
    advisor = result.scalar_one()

    case = Case(case_id=cid, sid=sid)
    case.intervention_status = InterventionStatus.ACCEPTED
    case.assigned_advisor_id = advisor.advisor_id
    case.mark_as_sent()
    case.record_booking(
        appointment_time=datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
        meeting_method=MeetingMethod.ONLINE,
    )
    case.start_supporting()

    await case_repository.add(case)
    await student_repository.session.commit()

    # Act: Call the resolve endpoint
    response = client.post(f'/api/v1/cases/{cid}/resolve')

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        'status': 'success',
        'message': 'Resolution request sent to student',
    }

    # Check status in DB
    updated_case = await case_repository.get_by_id(cid)
    assert updated_case.intervention_status == InterventionStatus.PENDING_REVIEW

    assert updated_case.closed_at is None

@pytest.mark.asyncio
async def test_book_appointment_case_not_found(client: TestClient) -> None:
    """Verify 404 is returned for a non-existent case."""
    random_id = uuid.uuid4()
    payload = {
        'appointment_time': '2026-05-11T10:00:00Z',
        'meeting_method': 'online',
    }
    response = client.post(f'/api/v1/cases/{random_id}/book', json=payload)
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
    payload = {
        'appointment_time': '2026-05-15T10:00:00Z',
        'meeting_method': MeetingMethod.ONLINE,
    }
    response = client.post(f'/api/v1/cases/{cid}/book', json=payload)

    # Assert
    assert response.status_code == 400
    assert 'Cannot transite to booked' in response.json()['detail']
