"""Unit tests for the OutboxMapper."""

import uuid
from datetime import UTC, datetime

from src.domain.events.advisor_events import AdvisorCreatedEvent
from src.domain.events.case_events import CaseAcceptedEvent
from src.domain.events.job_events import JobStatusChangedEvent
from src.domain.value_objects.status import JobStatus
from src.infrastructure.queue.outbox_mapper import OutboxMapper


def test_map_case_accepted_event():
    """Verify CaseAcceptedEvent maps to both background and websocket tasks."""
    case_id = uuid.uuid4()
    advisor_id = uuid.uuid4()
    event = CaseAcceptedEvent(case_id=case_id, advisor_id=advisor_id)
    
    tasks = OutboxMapper.map_to_tasks(event)
    
    assert len(tasks) == 2
    
    # Background task
    bg_task = next(t for t in tasks if t["task_name"] == "run_case_accepted_task")
    assert bg_task["kwargs"]["case_id"] == case_id
    assert bg_task["kwargs"]["advisor_id"] == advisor_id
    
    # WebSocket task
    ws_task = next(t for t in tasks if t["task_name"] == "websocket_broadcast")
    assert ws_task["kwargs"]["event_type"] == "CASE:STATUS_UPDATED"
    assert ws_task["kwargs"]["payload"]["case_id"] == str(case_id)


def test_map_job_status_changed_event():
    """Verify JobStatusChangedEvent maps to correct WebSocket event types."""
    job_id = uuid.uuid4()
    corr_id = uuid.uuid4()
    
    # Started
    event_started = JobStatusChangedEvent(
        job_id=job_id,
        status=JobStatus.RUNNING,
        correlation_id=corr_id,
        correlation_type="EMAIL_DRAFT"
    )
    tasks = OutboxMapper.map_to_tasks(event_started)
    ws_task = next(t for t in tasks if t["task_name"] == "websocket_broadcast")
    assert ws_task["kwargs"]["event_type"] == "JOB:STARTED"
    
    # Completed
    event_completed = JobStatusChangedEvent(
        job_id=job_id,
        status=JobStatus.SUCCESS,
        correlation_id=corr_id,
        correlation_type="EMAIL_DRAFT"
    )
    tasks = OutboxMapper.map_to_tasks(event_completed)
    ws_task = next(t for t in tasks if t["task_name"] == "websocket_broadcast")
    assert ws_task["kwargs"]["event_type"] == "JOB:COMPLETED"
    
    # Failed
    event_failed = JobStatusChangedEvent(
        job_id=job_id,
        status=JobStatus.ERROR,
        correlation_id=corr_id,
        correlation_type="EMAIL_DRAFT"
    )
    tasks = OutboxMapper.map_to_tasks(event_failed)
    ws_task = next(t for t in tasks if t["task_name"] == "websocket_broadcast")
    assert ws_task["kwargs"]["event_type"] == "JOB:FAILED"


def test_map_advisor_created_event():
    """Verify AdvisorCreatedEvent maps only to background task (no WS broadcast)."""
    advisor_id = uuid.uuid4()
    event = AdvisorCreatedEvent(advisor_id=advisor_id, email="test@ex.com", name="Test")
    
    tasks = OutboxMapper.map_to_tasks(event)
    
    assert len(tasks) == 1
    assert tasks[0]["task_name"] == "run_advisor_created_task"
