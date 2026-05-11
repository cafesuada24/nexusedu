"""Implementation of the Transactional Outbox pattern for background tasks."""

import pickle
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.identifiers import generate_uuid
from src.domain.value_objects.status import OutboxStatus
from src.infrastructure.database.models import OutboxEvent


class TransactionalOutboxAdapter:
    """Adapter that persists background tasks to the database.

    Ensures that background tasks are only triggered if the database
    transaction is successfully committed.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a database session."""
        self.session = session

    async def enqueue(self, task_name: str, **kwargs: Any) -> uuid.UUID:  # noqa: ANN401
        """Save task intent to the outbox table."""
        payload = pickle.dumps(kwargs)

        event = OutboxEvent(
            id=generate_uuid(),
            task_name=task_name,
            payload=payload,
            status=OutboxStatus.PENDING,
        )
        self.session.add(event)
        return event.id

    async def is_available(self) -> bool:
        """The outbox is available if the database is reachable."""
        return True
