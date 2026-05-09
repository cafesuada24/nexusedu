"""Service for processing pending outbox events and dispatching them to ARQ."""

import pickle
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.background_queue import BackgroundTaskQueue
from src.core.logger import logger
from src.domain.value_objects.status import OutboxStatus
from src.infrastructure.database.models import OutboxEvent


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
            .where(OutboxEvent.status == OutboxStatus.PENDING)
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

        logger.info(f'Outbox: Processing {len(events)} pending events.')

        for event in events:
            try:
                kwargs = pickle.loads(event.payload)
                await self.arq_queue.enqueue(event.task_name, **kwargs)

                event.status = OutboxStatus.PROCESSED
                event.processed_at = datetime.now(UTC)
                logger.debug(f'Outbox: Dispatched task {event.task_name} ({event.id})')
            except Exception as e:
                logger.error(
                    f'Outbox: Failed to dispatch event {event.id} ({event.task_name}): {e}',
                )
                event.status = OutboxStatus.FAILED
                event.error = str(e)
                event.processed_at = datetime.now(UTC)
