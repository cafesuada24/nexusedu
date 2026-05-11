"""Advisor-related domain events."""

from dataclasses import dataclass

from src.core.identifiers import EntityID
from src.domain.events.base import DomainEvent


@dataclass(frozen=True)
class AdvisorCreatedEvent(DomainEvent):
    """Event triggered when a new advisor is created."""

    advisor_id: EntityID
    email: str
    name: str
