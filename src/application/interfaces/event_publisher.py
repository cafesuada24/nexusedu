"""Interface for domain event publishing."""

from collections.abc import Sequence
from typing import Protocol

from src.domain.events.base import DomainEvent


class EventPublisher(Protocol):
    """Port for publishing domain events."""

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        """Publish a sequence of domain events."""
        ...
