"""Unit tests for the CaseCommandHandler's email generation logic."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.commands.case_commands import (
    CaseCommandHandler,
    GenerateEmailDraftCommand,
)
from src.domain.entities.intervention_email import InterventionEmail
from src.domain.exceptions import (
    CaseNotFoundError,
    MissingPerformanceDataError,
    StudentNameMissingError,
)


@pytest.fixture
def mock_repos():
    return {
        'student_repo': AsyncMock(),
        'email_repo': AsyncMock(),
        'case_repo': AsyncMock(),
        'advisor_repo': AsyncMock(),
        'job_repo': AsyncMock(),
        'task_queue': AsyncMock(),
        'event_publisher': AsyncMock(),
        'availability_service': MagicMock(),
        'email_drafting_service': AsyncMock(),
    }


@pytest.fixture
def handler(mock_repos):
    return CaseCommandHandler(**mock_repos)


@pytest.mark.asyncio
async def test_generate_email_draft_success(handler, mock_repos):
    # Arrange
    case_id = uuid.uuid4()
    sid = uuid.uuid4()
    command = GenerateEmailDraftCommand(
        case_id=case_id,
        job_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        booking_link='http://test.link'
    )

    mock_case = MagicMock()
    mock_case.case_id = case_id
    mock_case.sid = sid
    mock_repos['case_repo'].get_by_id.return_value = mock_case

    mock_email = MagicMock(spec=InterventionEmail)
    mock_email.mark_as_generating = MagicMock()
    mock_email.set_draft_content = MagicMock()
    mock_repos['email_repo'].get_by_case.return_value = mock_email

    mock_email = MagicMock(spec=InterventionEmail)
    mock_email.mark_as_generating = MagicMock()
    mock_repos['email_repo'].get_by_case.return_value = mock_email

    mock_student = MagicMock()
    mock_student.student_name = "Test Student"
    mock_repos['student_repo'].get_by_id.return_value = mock_student

    mock_repos['student_repo'].get_recent_performance.return_value = [
        {'yr': 2024, 'sem': 1, 'wk': 5, 'score': 85, 'status': 'STABLE'}
    ]

    mock_repos['email_drafting_service'].generate_draft.return_value = ("Generated Subject", "Generated Body")

    # Act
    await handler.handle_generate_email_draft(command)

    # Assert
    mock_repos['email_drafting_service'].generate_draft.assert_called_once_with(
        "Test Student",
        "Trend: Year 2024 Sem 1 Week 5: Score 85 (STABLE)",
        "http://test.link"
    )
    mock_email.set_draft_content.assert_called_once_with(
        "Generated Subject",
        "Generated Body"
    )


@pytest.mark.asyncio
async def test_generate_email_draft_missing_student_name(handler, mock_repos):
    # Arrange
    case_id = uuid.uuid4()
    sid = uuid.uuid4()
    command = GenerateEmailDraftCommand(case_id=case_id, job_id=uuid.uuid4(), user_id=uuid.uuid4())

    mock_case = MagicMock()
    mock_case.sid = sid
    mock_repos['case_repo'].get_by_id.return_value = mock_case

    mock_email = MagicMock(spec=InterventionEmail)
    mock_email.mark_as_generating = MagicMock()
    mock_repos['email_repo'].get_by_case.return_value = mock_email

    mock_student = MagicMock()
    mock_student.student_name = None  # Missing name
    mock_repos['student_repo'].get_by_id.return_value = mock_student

    # Act & Assert
    with pytest.raises(StudentNameMissingError):
        await handler.handle_generate_email_draft(command)


@pytest.mark.asyncio
async def test_generate_email_draft_missing_performance_data(handler, mock_repos):
    # Arrange
    case_id = uuid.uuid4()
    sid = uuid.uuid4()
    command = GenerateEmailDraftCommand(case_id=case_id, job_id=uuid.uuid4(), user_id=uuid.uuid4())

    mock_case = MagicMock()
    mock_case.sid = sid
    mock_repos['case_repo'].get_by_id.return_value = mock_case

    mock_email = MagicMock(spec=InterventionEmail)
    mock_email.mark_as_generating = MagicMock()
    mock_repos['email_repo'].get_by_case.return_value = mock_email

    mock_student = MagicMock()
    mock_student.student_name = "Test Student"
    mock_repos['student_repo'].get_by_id.return_value = mock_student

    mock_repos['student_repo'].get_recent_performance.return_value = []  # Empty data

    # Act & Assert
    with pytest.raises(MissingPerformanceDataError):
        await handler.handle_generate_email_draft(command)
