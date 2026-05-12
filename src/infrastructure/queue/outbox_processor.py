"""Service for processing pending outbox events and dispatching them to ARQ."""

import pickle
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.background_queue import BackgroundTaskQueue
from src.domain.value_objects.status import OutboxStatus
from src.infrastructure.database.models import OutboxEvent

logger = structlog.get_logger(__name__)
# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5


class OutboxProcessor:
    """Processor that forwards outbox events to the real background queue."""

    def __init__(self, session: AsyncSession, arq_queue: BackgroundTaskQueue) -> None:
        """Initialize with database session and real task queue."""
        self.session = session
        self.arq_queue = arq_queue

    async def process_pending_events(self, limit: int = 50) -> None:
        """Fetch and dispatch pending outbox events."""
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.status.in_([OutboxStatus.PENDING, OutboxStatus.FAILED]))
            .where(
                (OutboxEvent.processed_at == None)  # noqa: E711
                | (
                    OutboxEvent.processed_at
                    <= datetime.now(UTC) - timedelta(seconds=RETRY_DELAY_SECONDS)
                )
            )
            .order_by(OutboxEvent.created_at)
            .limit(limit)
        )

        # Apply SKIP LOCKED for PostgreSQL to support safe concurrent processing
        if self.session.bind and self.session.bind.dialect.name == 'postgresql':
            stmt = stmt.with_for_update(skip_locked=True)

        result = await self.session.execute(stmt)
        events = result.scalars().all()

        if not events:
            return

        logger.info(f'Outbox: Processing {len(events)} pending/failed events.')

        for event in events:
            # Skip if max retries reached
            if event.error and 'Retry limit reached' in event.error:
                continue

            try:
                kwargs = pickle.loads(event.payload)
                await self.arq_queue.enqueue(event.task_name, **kwargs)

                event.status = OutboxStatus.PROCESSED
                event.processed_at = datetime.now(UTC)
                logger.debug(f'Outbox: Dispatched task {event.task_name} ({event.id})')
            except Exception as e:
                # Basic retry logic using processed_at as last attempt timestamp
                current_error = str(e)
                retry_count = (
                    event.error.count('Retry attempt') + 1 if event.error else 1
                )

                if retry_count < MAX_RETRIES:
                    event.status = OutboxStatus.FAILED
                    event.error = f'Retry attempt {retry_count}: {current_error}'
                    logger.warning(
                        f'Outbox: Transient failure for {event.id} ({event.task_name}). '
                        f'Will retry. Error: {current_error}',
                    )
                else:
                    event.status = OutboxStatus.FAILED
                    event.error = f'Retry limit reached ({MAX_RETRIES}): {current_error}'
                    logger.error(
                        f'Outbox: Permanent failure for {event.id} ({event.task_name}): {current_error}',
                    )

                event.processed_at = datetime.now(UTC)
