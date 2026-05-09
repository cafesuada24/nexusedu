"""Case-related domain events."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.events.base import DomainEvent
from src.domain.value_objects.status import MeetingMethod


@dataclass(frozen=True)
class CaseAcceptedEvent(DomainEvent):
    """Event triggered when a case is accepted by an advisor."""

    case_id: UUID
    advisor_id: UUID


@dataclass(frozen=True)
class StudentBookedEvent(DomainEvent):
    """Event triggered when a student books an appointment."""

    case_id: UUID
    appointment_time: datetime
    meeting_method: MeetingMethod
    notes: str | None = None


@dataclass(frozen=True)
class CaseReviewRequestedEvent(DomainEvent):
    """Event triggered when an advisor requests a case resolution, pending student review."""

    case_id: UUID
    advisor_id: UUID


@dataclass(frozen=True)
class CaseResolvedEvent(DomainEvent):
    """Event triggered when a case is successfully resolved after review."""

    case_id: UUID
    advisor_id: UUID
    satisfaction: str | None = None
    comment: str | None = None


@dataclass(frozen=True)
class CaseFailedEvent(DomainEvent):
    """Event triggered when a case resolution fails based on student review."""

    case_id: UUID
    advisor_id: UUID
    satisfaction: str | None = None
    comment: str | None = None
