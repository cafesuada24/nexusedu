import uuid
import pytest
import jwt
from datetime import UTC, datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities.case import Case
from src.domain.value_objects.status import InterventionStatus
from src.domain.value_objects.student_satisfaction import StudentSatisfaction
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.student_repository import StudentRepository
from src.infrastructure.database.models import User, Advisor
from src.core.config import config

@pytest.mark.asyncio
async def test_submit_case_review_success(
    client: TestClient,
    case_repository: CaseRepository,
    student_repository: StudentRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that a student can submit a review and resolve the case."""
    sid = uuid.uuid4()
    cid = uuid.uuid4()

    # Setup: Create student and case in PENDING_REVIEW status
    await student_repository.ingest_students(
        [{'sid': sid, 'student_name': 'Test Student', 'email': 'student@example.com'}]
    )

    case = Case(case_id=cid, sid=sid)
    case.intervention_status = InterventionStatus.PENDING_REVIEW
    # We need an assigned advisor for finalize_resolution
    case.assigned_advisor_id = uuid.uuid4() 
    
    await case_repository.add(case)
    await student_repository.session.commit()

    # Generate JWT token
    payload = {
        'case_id': str(cid),
        'exp': datetime.now(UTC) + timedelta(days=1),
        'iat': datetime.now(UTC),
    }
    token = jwt.encode(payload, config.jwt_secret or 'insecure_default', algorithm='HS256')

    # Act: Submit review
    response = client.post(
        f'/api/v1/cases/review?token={token}',
        json={
            'satisfaction': StudentSatisfaction.VERY_GOOD,
            'comment': 'Great support!'
        }
    )

    # Assert
    assert response.status_code == 200
    assert response.json()['status'] == 'success'

    # Check status in DB
    updated_case = await case_repository.get_by_id(cid)
    assert updated_case.intervention_status == InterventionStatus.RESOLVED
    assert updated_case.closed_at is not None

@pytest.mark.asyncio
async def test_submit_case_review_failure_state(
    client: TestClient,
    case_repository: CaseRepository,
    student_repository: StudentRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that a BAD review transitions the case to FAILED status."""
    sid = uuid.uuid4()
    cid = uuid.uuid4()

    await student_repository.ingest_students(
        [{'sid': sid, 'student_name': 'Test Student', 'email': 'student@example.com'}]
    )

    case = Case(case_id=cid, sid=sid)
    case.intervention_status = InterventionStatus.PENDING_REVIEW
    case.assigned_advisor_id = uuid.uuid4()
    
    await case_repository.add(case)
    await student_repository.session.commit()

    payload = {
        'case_id': str(cid),
        'exp': datetime.now(UTC) + timedelta(days=1),
    }
    token = jwt.encode(payload, config.jwt_secret or 'insecure_default', algorithm='HS256')

    # Act: Submit BAD review
    response = client.post(
        f'/api/v1/cases/review?token={token}',
        json={
            'satisfaction': StudentSatisfaction.VERY_BAD,
            'comment': 'Did not help at all.'
        }
    )

    # Assert
    assert response.status_code == 200
    
    updated_case = await case_repository.get_by_id(cid)
    assert updated_case.intervention_status == InterventionStatus.FAILED

@pytest.mark.asyncio
async def test_submit_case_review_invalid_token(client: TestClient) -> None:
    """Verify that an invalid token returns 401."""
    response = client.post(
        '/api/v1/cases/review?token=invalid-token',
        json={
            'satisfaction': StudentSatisfaction.GOOD,
            'comment': 'Nice.'
        }
    )
    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid token'
