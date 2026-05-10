"""Advisor-related domain events."""

from dataclasses import dataclass
from uuid import UUID

from src.domain.events.base import DomainEvent


@dataclass(frozen=True)
class AdvisorCreatedEvent(DomainEvent):
    """Event triggered when a new advisor is created."""

    advisor_id: UUID
    email: str
    name: str
