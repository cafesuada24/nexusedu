"""Unit tests for the CaseCommandHandler's email generation logic."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.commands.case_commands import (
    CaseCommandHandler,
    GenerateEmailDraftCommand,
)
from src.domain.entities.intervention_email import InterventionEmail
from src.domain.exceptions import (
    AdvisorNotFoundError,
    CaseNotFoundError,
    MissingPerformanceDataError,
    StudentNameMissingError,
)


@pytest.fixture
def mock_uow():
    uow = MagicMock()
    uow.students = AsyncMock()
    uow.emails = AsyncMock()
    uow.cases = AsyncMock()
    uow.advisors = AsyncMock()
    uow.jobs = AsyncMock()
    uow.notification = AsyncMock()
    uow.user_settings = AsyncMock()
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    return uow


@pytest.fixture
def mock_services():
    return {
        'availability_service': AsyncMock(),
        'email_drafting_service': AsyncMock(),
    }


@pytest.fixture
def handler(mock_uow, mock_services):
    return CaseCommandHandler(uow=mock_uow, **mock_services)


@pytest.mark.asyncio
async def test_book_appointment_notifies_advisor(handler, mock_uow, mock_services):
    # Arrange
    case_id = uuid.uuid4()
    advisor_id = uuid.uuid4()
    user_id = uuid.uuid4()
    sid = uuid.uuid4()
    from src.application.dtos.case_dtos import BookAppointmentCommand
    from src.domain.value_objects.status import MeetingMethod
    
    command = BookAppointmentCommand(
        case_id=case_id,
        appointment_time=datetime.now(UTC),
        meeting_method=MeetingMethod.ONLINE,
        duration_minutes=30,
        notes="Test notes"
    )

    mock_case = MagicMock()
    mock_case.case_id = case_id
    mock_case.sid = sid
    mock_case.assigned_advisor_id = advisor_id
    mock_uow.cases.get_by_id.return_value = mock_case

    mock_advisor = MagicMock()
    mock_advisor.user_id = user_id
    mock_uow.advisors.get_by_id.return_value = mock_advisor

    mock_student = MagicMock()
    mock_student.student_name = "Test Student"
    mock_uow.students.get_by_id.return_value = mock_student

    mock_services['availability_service'].is_slot_available.return_value = True

    # Act
    await handler.handle_book_appointment(command)

    # Assert
    mock_uow.notification.add.assert_called_once()
    notification = mock_uow.notification.add.call_args[0][0]
    assert notification.user_id == user_id
    assert "Test Student" in notification.body
    assert str(case_id) in str(notification.payload['case_id'])
    mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_generate_email_draft_success(handler, mock_uow, mock_services):
    # Arrange
    case_id = uuid.uuid4()
    sid = uuid.uuid4()
    command = GenerateEmailDraftCommand(
        case_id=case_id,
        job_id=uuid.uuid4(),
        user_id=uuid.uuid4()
    )

    mock_case = MagicMock()
    mock_case.case_id = case_id
    mock_case.sid = sid
    mock_uow.cases.get_by_id.return_value = mock_case

    mock_email = MagicMock(spec=InterventionEmail)
    mock_email.mark_as_generating = MagicMock()
    mock_email.set_draft_content = MagicMock()
    mock_uow.emails.get_by_case.return_value = mock_email

    mock_student = MagicMock()
    mock_student.student_name = "Test Student"
    mock_uow.students.get_by_id.return_value = mock_student

    mock_uow.students.get_recent_performance.return_value = [
        {'yr': 2024, 'sem': 1, 'wk': 5, 'score': 85, 'status': 'STABLE'}
    ]

    mock_settings = MagicMock()
    mock_settings.ai_tone = "professional"
    mock_settings.safety_rules = ["rule1"]
    mock_uow.user_settings.get_by_user_id.return_value = mock_settings

    mock_services['email_drafting_service'].generate_draft.return_value = ("Generated Subject", "Generated Body")

    # Act
    await handler.handle_generate_email_draft(command)

    # Assert
    mock_services['email_drafting_service'].generate_draft.assert_called_once_with(
        "Test Student",
        "Trend: Year 2024 Sem 1 Week 5: Score 85 (STABLE)",
        ai_tone="professional",
        safety_rules=["rule1"]
    )
    mock_email.set_draft_content.assert_called_once_with(
        "Generated Subject",
        "Generated Body"
    )
    mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_generate_email_draft_missing_student_name(handler, mock_uow, mock_services):
    # Arrange
    case_id = uuid.uuid4()
    sid = uuid.uuid4()
    command = GenerateEmailDraftCommand(case_id=case_id, job_id=uuid.uuid4(), user_id=uuid.uuid4())

    mock_case = MagicMock()
    mock_case.sid = sid
    mock_uow.cases.get_by_id.return_value = mock_case

    mock_email = MagicMock(spec=InterventionEmail)
    mock_email.mark_as_generating = MagicMock()
    mock_uow.emails.get_by_case.return_value = mock_email

    mock_student = MagicMock()
    mock_student.student_name = None  # Missing name
    mock_uow.students.get_by_id.return_value = mock_student

    # Act & Assert
    with pytest.raises(StudentNameMissingError):
        await handler.handle_generate_email_draft(command)


@pytest.mark.asyncio
async def test_generate_email_draft_missing_performance_data(handler, mock_uow, mock_services):
    # Arrange
    case_id = uuid.uuid4()
    sid = uuid.uuid4()
    command = GenerateEmailDraftCommand(case_id=case_id, job_id=uuid.uuid4(), user_id=uuid.uuid4())

    mock_case = MagicMock()
    mock_case.sid = sid
    mock_uow.cases.get_by_id.return_value = mock_case

    mock_email = MagicMock(spec=InterventionEmail)
    mock_email.mark_as_generating = MagicMock()
    mock_uow.emails.get_by_case.return_value = mock_email

    mock_student = MagicMock()
    mock_student.student_name = "Test Student"
    mock_uow.students.get_by_id.return_value = mock_student

    mock_uow.students.get_recent_performance.return_value = []  # Empty data

    # Act & Assert
    with pytest.raises(MissingPerformanceDataError):
        await handler.handle_generate_email_draft(command)
