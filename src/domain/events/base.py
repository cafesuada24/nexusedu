"""Base domain event class."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

import uuid6


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base class for all domain events."""

    event_id: UUID = field(default_factory=uuid6.uuid7)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
