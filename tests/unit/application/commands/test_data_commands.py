"""Tests for DataCommandHandler orchestration."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.commands.data_commands import DataCommandHandler
from src.domain.value_objects.status import InterventionStatus, RiskStatus


@pytest.fixture
def mock_uow():
    uow = MagicMock()
    uow.students = AsyncMock()
    uow.activities = AsyncMock()
    uow.history = AsyncMock()
    uow.cases = AsyncMock()
    uow.jobs = AsyncMock()
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    uow.enqueue = AsyncMock()
    uow.collect_events = MagicMock()
    return uow


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    return engine


@pytest.fixture
def handler(mock_uow, mock_engine):
    return DataCommandHandler(
        uow=mock_uow,
        anomaly_engine=mock_engine,
    )


@pytest.mark.asyncio
async def test_run_anomaly_detection_orchestration(handler, mock_uow, mock_engine):
    """Verify that DataCommandHandler correctly orchestrates the anomaly detection."""
    sid = uuid.uuid4()
    # Setup data
    mock_uow.activities.get_weekly_averages.return_value = [
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
    mock_uow.history.get_all_history.return_value = []

    # Mock engine return
    new_records = [{'history_id': str(uuid.uuid4()), 'sid': sid, 'week': 2}]
    risk_statuses = {sid: RiskStatus.CRITICAL}
    mock_engine.run.return_value = (new_records, risk_statuses)

    # Mock student for transition
    mock_student = MagicMock()
    mock_uow.students.get_by_id.return_value = mock_student
    mock_uow.cases.get_active_case.return_value = None

    # Execute
    new_at_risk = await handler._run_anomaly_detection()

    # Verify
    assert sid in (s[0] for s in new_at_risk)
    mock_uow.history.batch_create_history.assert_called_once_with(new_records)

    # Verify student update
    mock_student.update_risk.assert_called_with(RiskStatus.CRITICAL)
    mock_uow.students.save.assert_called_with(mock_student)

    # Verify case creation
    mock_uow.cases.add.assert_called_once()

    # Verify background task enqueued
    mock_uow.enqueue.assert_called_once_with('run_batch_case_overviews_task')

    # Verify engine was called with grouped data
    args, _ = mock_engine.run.call_args
    student_data = args[0]
    assert sid in student_data
    assert len(student_data[sid]) == 2


@pytest.mark.asyncio
async def test_handle_ingest_data(handler, mock_uow, mock_engine):
    """Verify that handle_ingest_data enqueues students and activities and publishes event."""
    from src.application.dtos.data_dtos import DataIngestionCommand, DataSourceDTO
    from src.domain.entities.data_ingestion import DataIngestion
    from src.domain.events.data_events import DataIngestedEvent

    command = DataIngestionCommand(
        data_sources=[
            DataSourceDTO(source_type='sis', records=[{'sid': 's1'}]),
            DataSourceDTO(source_type='lms', records=[{'sid': 's1', 'score': 10}]),
        ]
    )

    # Mock anomaly detection
    handler._run_anomaly_detection = AsyncMock(return_value=[(uuid.uuid4(), uuid.uuid4())])

    # Execute
    job_id = uuid.uuid4()
    result = await handler.handle_ingest_data(command, job_id=job_id)

    # Verify ingestion calls
    mock_uow.students.ingest_students.assert_called_once()
    mock_uow.activities.ingest_activities.assert_called_once()

    # Verify event collected
    mock_uow.collect_events.assert_called_once()
    args, _ = mock_uow.collect_events.call_args
    ingestion = args[0]
    assert isinstance(ingestion, DataIngestion)
    assert len(ingestion.domain_events) == 1
    assert isinstance(ingestion.domain_events[0], DataIngestedEvent)
    assert ingestion.domain_events[0].job_id == job_id

    assert result['results']
    assert len(result['new_sids']) == 1
