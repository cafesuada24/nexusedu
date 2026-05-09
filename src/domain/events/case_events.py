"""Case-related domain events."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.events.base import DomainEvent


@dataclass(frozen=True)
class CaseAcceptedEvent(DomainEvent):
    """Event triggered when a case is accepted by an advisor."""

    case_id: UUID
    advisor_id: UUID
    occurred_at: datetime


@dataclass(frozen=True)
class StudentBookedEvent(DomainEvent):
    """Event triggered when a student books an appointment."""

    case_id: UUID
    occurred_at: datetime


@dataclass(frozen=True)
class CaseResolvedEvent(DomainEvent):
    """Event triggered when a case is resolved."""

    case_id: UUID
    advisor_id: UUID
    occurred_at: datetime
