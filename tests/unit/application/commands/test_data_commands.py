"""Tests for DataCommandHandler orchestration."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.commands.data_commands import DataCommandHandler
from src.domain.value_objects.status import InterventionStatus, RiskStatus


@pytest.fixture
def mock_repos():
    return {
        'student': MagicMock(),
        'activity': MagicMock(),
        'history': MagicMock(),
        'settings': MagicMock(),
        'idempotency': MagicMock(),
        'job': MagicMock(),
        'case': MagicMock(),
    }


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    return engine


@pytest.fixture
def handler(mock_repos, mock_engine):
    # Initialize all awaited methods as AsyncMock
    mock_repos['activity'].get_weekly_averages = AsyncMock()
    mock_repos['history'].get_all_history = AsyncMock()
    mock_repos['history'].batch_create_history = AsyncMock()
    mock_repos['student'].get_by_id = AsyncMock()
    mock_repos['student'].save = AsyncMock()
    mock_repos['case'].get_active_case = AsyncMock()
    mock_repos['case'].add = AsyncMock()

    return DataCommandHandler(
        student_repo=mock_repos['student'],
        activity_repo=mock_repos['activity'],
        history_repo=mock_repos['history'],
        case_repo=mock_repos['case'],
        job_repo=mock_repos['job'],
        anomaly_engine=mock_engine,
    )


@pytest.mark.asyncio
async def test_run_anomaly_detection_orchestration(handler, mock_repos, mock_engine):
    """Verify that DataCommandHandler correctly orchestrates the anomaly detection."""
    sid = uuid.uuid4()
    # Setup data
    mock_repos['activity'].get_weekly_averages.return_value = [
        {
            'sid': sid,
            'avg_score': 90.0,
            'academic_year': 2024,
            'semester': 1,
            'week': 1,
        },
        {
            'sid': sid,
            'avg_score': 40.0,
            'academic_year': 2024,
            'semester': 1,
            'week': 2,
        },
    ]
    mock_repos['history'].get_all_history.return_value = []

    # Mock engine return
    new_records = [{'history_id': str(uuid.uuid4()), 'sid': sid, 'week': 2}]
    risk_statuses = {sid: RiskStatus.CRITICAL}
    mock_engine.run.return_value = (new_records, risk_statuses)

    # Mock student for transition
    mock_student = MagicMock()
    mock_repos['student'].get_by_id.return_value = mock_student
    mock_repos['case'].get_active_case.return_value = None

    # Execute
    new_at_risk = await handler._run_anomaly_detection()

    # Verify
    assert sid in (s[0] for s in new_at_risk)
    mock_repos['history'].batch_create_history.assert_called_once_with(new_records)
    
    # Verify student update
    mock_student.update_risk.assert_called_with(RiskStatus.CRITICAL)
    mock_repos['student'].save.assert_called_with(mock_student)
    
    # Verify case creation
    mock_repos['case'].add.assert_called_once()

    # Verify engine was called with grouped data
    args, _ = mock_engine.run.call_args
    student_data = args[0]
    assert sid in student_data
    assert len(student_data[sid]) == 2
