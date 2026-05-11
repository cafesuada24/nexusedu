"""Base domain event class."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.core.identifiers import EntityID, generate_uuid


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base class for all domain events."""

    event_id: EntityID = field(default_factory=generate_uuid)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
