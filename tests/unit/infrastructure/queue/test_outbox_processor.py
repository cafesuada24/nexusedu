"""Unit tests for the OutboxProcessor."""

import pickle
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.value_objects.status import OutboxStatus
from src.infrastructure.database.models import OutboxEvent
from src.infrastructure.queue.outbox_processor import OutboxProcessor


@pytest.fixture
def arq_queue() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def ws_publisher() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def processor(
    test_db_session: AsyncSession,
    arq_queue: AsyncMock,
    ws_publisher: AsyncMock,
) -> OutboxProcessor:
    return OutboxProcessor(
        session=test_db_session,
        arq_queue=arq_queue,
        ws_publisher=ws_publisher,
    )


@pytest.mark.asyncio
async def test_process_background_task(
    test_db_session: AsyncSession,
    processor: OutboxProcessor,
    arq_queue: AsyncMock,
) -> None:
    """Verify that background tasks are dispatched to ARQ."""
    payload = {"arg": "val"}
    event = OutboxEvent(
        id=uuid.uuid4(),
        task_name="test_task",
        payload=pickle.dumps(payload),
        status=OutboxStatus.PENDING,
    )
    test_db_session.add(event)
    await test_db_session.commit()

    await processor.process_pending_events()

    # Verify ARQ called
    arq_queue.enqueue.assert_called_once_with("test_task", arg="val")

    # Verify event status updated
    await test_db_session.refresh(event)
    assert event.status == OutboxStatus.PROCESSED
    assert event.processed_at is not None


@pytest.mark.asyncio
async def test_process_websocket_broadcast(
    test_db_session: AsyncSession,
    processor: OutboxProcessor,
    ws_publisher: AsyncMock,
) -> None:
    """Verify that websocket_broadcast tasks are dispatched to WebSocketEventPublisher."""
    payload = {
        "event_type": "TEST_EVT",
        "payload": {"foo": "bar"},
        "user_id": str(uuid.uuid4()),
    }
    event = OutboxEvent(
        id=uuid.uuid4(),
        task_name="websocket_broadcast",
        payload=pickle.dumps(payload),
        status=OutboxStatus.PENDING,
    )
    test_db_session.add(event)
    await test_db_session.commit()

    await processor.process_pending_events()

    # Verify WS publisher called
    ws_publisher.publish.assert_called_once_with(**payload)

    # Verify event status updated
    await test_db_session.refresh(event)
    assert event.status == OutboxStatus.PROCESSED


@pytest.mark.asyncio
async def test_retry_on_failure(
    test_db_session: AsyncSession,
    processor: OutboxProcessor,
    arq_queue: AsyncMock,
) -> None:
    """Verify that failed tasks are retried and eventually marked as permanent failure."""
    arq_queue.enqueue.side_effect = Exception("Transient error")
    
    event = OutboxEvent(
        id=uuid.uuid4(),
        task_name="fail_task",
        payload=pickle.dumps({}),
        status=OutboxStatus.PENDING,
    )
    test_db_session.add(event)
    await test_db_session.commit()

    # Attempt 1
    await processor.process_pending_events()
    await test_db_session.refresh(event)
    assert event.status == OutboxStatus.FAILED
    assert "Retry attempt 1" in event.error

    # Attempt 2
    event.processed_at = datetime.now(UTC) - timedelta(minutes=1) # Fast forward time
    await test_db_session.commit()
    await processor.process_pending_events()
    await test_db_session.refresh(event)
    assert "Retry attempt 2" in event.error

    # Attempt 3 - Permanent failure
    event.processed_at = datetime.now(UTC) - timedelta(minutes=1)
    await test_db_session.commit()
    await processor.process_pending_events()
    await test_db_session.refresh(event)
    assert "Retry limit reached" in event.error
    assert event.status == OutboxStatus.FAILED
