"""Unit tests for EmailApplicationService."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.email_application_service import EmailApplicationService
from src.core.identifiers import generate_uuid
from src.domain.value_objects.status import RiskStatus


@pytest.fixture
def mock_uow():
    uow = AsyncMock()
    # Mocking contexts
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None
    return uow


@pytest.fixture
def mock_email_sending_service():
    return AsyncMock()


@pytest.fixture
def mock_gamification_app_service():
    return AsyncMock()


@pytest.fixture
def mock_gamification_service():
    mock = MagicMock()
    mock.Action.SEND_EMAIL = "SEND_EMAIL"
    return mock


@pytest.fixture
def service(
    mock_uow,
    mock_email_sending_service,
    mock_gamification_app_service,
    mock_gamification_service,
):
    return EmailApplicationService(
        uow=mock_uow,
        email_sending_service=mock_email_sending_service,
        gamification_app_service=mock_gamification_app_service,
        gamification_service=mock_gamification_service,
    )


@pytest.mark.asyncio
async def test_send_intervention_email_skips_if_already_sent(
    service,
    mock_uow,
    mock_email_sending_service,
):
    """Verify that email is not sent if it already has a sent_at timestamp."""
    case_id = uuid.uuid4()
    job_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Setup mocks
    mock_case = MagicMock()
    mock_case.assigned_advisor_id = uuid.uuid4()
    mock_uow.cases.get_by_id = AsyncMock(return_value=mock_case)

    mock_email = MagicMock()
    mock_email.is_sent = True  # Already sent!
    mock_uow.emails.get_by_case = AsyncMock(return_value=mock_email)

    # Execute
    await service.send_intervention_email(case_id, job_id, user_id)

    # Verify
    mock_email_sending_service.send_email.assert_not_called()


@pytest.mark.asyncio
async def test_send_intervention_email_success(
    service,
    mock_uow,
    mock_email_sending_service,
    mock_gamification_app_service,
):
    """Verify successful email dispatch and record updates."""
    case_id = uuid.uuid4()
    job_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Setup mocks
    mock_case = MagicMock()
    mock_case.case_id = case_id
    mock_case.assigned_advisor_id = uuid.uuid4()
    mock_case.sid = uuid.uuid4()
    mock_case.assigned_at = datetime.now(UTC)
    
    mock_email = MagicMock()
    mock_email.email_id = uuid.uuid4()
    mock_email.is_sent = False
    mock_email.subject = "Subject"
    mock_email.body = "Body"

    mock_student = MagicMock()
    mock_student.email = "student@example.com"
    mock_student.current_risk_status = RiskStatus.CRITICAL

    mock_advisor = MagicMock()
    mock_advisor.email = "advisor@example.com"
    mock_advisor.user_id = uuid.uuid4()

    mock_settings = MagicMock()
    mock_settings.signature = "-- Best regards"

    # Explicitly set AsyncMocks
    mock_uow.cases.get_by_id = AsyncMock(return_value=mock_case)
    mock_uow.emails.get_by_case = AsyncMock(return_value=mock_email)
    mock_uow.students.get_by_id = AsyncMock(return_value=mock_student)
    mock_uow.advisors.get_by_id = AsyncMock(return_value=mock_advisor)
    mock_uow.user_settings.get_by_user_id = AsyncMock(return_value=mock_settings)

    # Execute
    await service.send_intervention_email(case_id, job_id, user_id)

    # Verify
    mock_email_sending_service.send_email.assert_called_once_with(
        to_email="student@example.com",
        subject="Subject",
        body="Body\n\n-- Best regards",
        reply_to="advisor@example.com",
    )
    
    # Verify persistence
    assert mock_uow.commit.called
    mock_email.mark_as_sent.assert_called_once()
    mock_gamification_app_service.award_points.assert_called_once()
