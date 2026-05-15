"""Case-related domain events."""

from dataclasses import dataclass
from datetime import datetime

from src.core.identifiers import EntityID
from src.domain.events.base import DomainEvent
from src.domain.value_objects.status import MeetingMethod
from src.domain.value_objects.student_satisfaction import StudentSatisfaction


@dataclass(frozen=True)
class CaseAcceptedEvent(DomainEvent):
    """Event triggered when a case is accepted by an advisor."""

    case_id: EntityID
    advisor_id: EntityID


@dataclass(frozen=True)
class StudentBookedEvent(DomainEvent):
    """Event triggered when a student books an appointment."""

    case_id: EntityID
    appointment_time: datetime
    meeting_method: MeetingMethod
    notes: str | None = None


@dataclass(frozen=True)
class CaseSupportingStartedEvent(DomainEvent):
    """Event triggered when an advisor starts supporting a student."""

    case_id: EntityID
    advisor_id: EntityID


@dataclass(frozen=True)
class CaseReviewRequestedEvent(DomainEvent):
    """Event triggered when an advisor requests a case resolution, pending student review."""

    case_id: EntityID
    advisor_id: EntityID


@dataclass(frozen=True)
class CaseResolvedEvent(DomainEvent):
    """Event triggered when a case is successfully resolved after review."""

    case_id: EntityID
    advisor_id: EntityID
    satisfaction: StudentSatisfaction
    comment: str | None = None


@dataclass(frozen=True)
class CaseFailedEvent(DomainEvent):
    """Event triggered when a case resolution fails based on student review."""

    case_id: EntityID
    advisor_id: EntityID
    satisfaction: StudentSatisfaction
    comment: str | None = None


@dataclass(frozen=True)
class EmailDraftRequestedEvent(DomainEvent):
    """Event triggered when an AI email draft generation is requested."""

    case_id: EntityID
    job_id: EntityID
    user_id: EntityID


@dataclass(frozen=True)
class InterventionEmailSentEvent(DomainEvent):
    """Event triggered when an intervention email is sent."""

    case_id: EntityID
    job_id: EntityID
    user_id: EntityID


@dataclass(frozen=True)
class CaseOverviewGeneratedEvent(DomainEvent):
    """Event triggered when an AI academic overview is generated."""

    case_id: EntityID
    academic_summary: str
    action_keys: list[str]
