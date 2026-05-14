"""Case domain entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from src.core.identifiers import EntityID, generate_uuid
from src.domain.entities.appointment import Appointment
from src.domain.entities.base import AggregateRoot
from src.domain.events.base import DomainEvent
from src.domain.events.case_events import (
    CaseAcceptedEvent,
    CaseFailedEvent,
    CaseResolvedEvent,
    CaseReviewRequestedEvent,
    EmailDraftRequestedEvent,
    InterventionEmailSentEvent,
    StudentBookedEvent,
)
from src.domain.exceptions import (
    CaseAlreadyAssignedError,
    InvalidStateTransitionError,
    ValidationError,
)
from src.domain.value_objects.status import InterventionStatus, MeetingMethod

_INTERVENTION_STATUS_TRANSITION = {
    InterventionStatus.NEW: [InterventionStatus.ACCEPTED, InterventionStatus.DISMISSED],
    InterventionStatus.ACCEPTED: [
        InterventionStatus.SENT,
        InterventionStatus.EXPIRED,
    ],
    InterventionStatus.SENT: [
        InterventionStatus.BOOKED,
        InterventionStatus.EXPIRED,
    ],
    InterventionStatus.BOOKED: [
        InterventionStatus.SUPPORTING,
        InterventionStatus.EXPIRED,
    ],
    InterventionStatus.SUPPORTING: [
        InterventionStatus.PENDING_REVIEW,
        InterventionStatus.EXPIRED,
    ],
    InterventionStatus.PENDING_REVIEW: [
        InterventionStatus.RESOLVED,
        InterventionStatus.FAILED,
    ],
    # Terminal states have no outgoing transitions
    InterventionStatus.RESOLVED: [],
    InterventionStatus.FAILED: [],
    InterventionStatus.DISMISSED: [],
    InterventionStatus.EXPIRED: [],
}


@dataclass
class Case(AggregateRoot):
    """Represents an intervention case for a student."""

    sid: EntityID
    case_id: EntityID = field(default_factory=generate_uuid)
    intervention_status: InterventionStatus = InterventionStatus.NEW
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    assigned_at: datetime | None = None
    closed_at: datetime | None = None
    assigned_advisor_id: EntityID | None = None
    appointment: Appointment | None = None
    academic_summary: str | None = None
    action_keys: list[str] | None = None
    version: int = field(default=0)

    @property
    def time_to_resolve(self) -> timedelta | None:
        """Calculates the duration between assignment and resolution.

        Returns None if the case is not yet closed.
        """
        if self.assigned_at and self.closed_at:
            return self.closed_at - self.assigned_at
        return None

    @property
    def is_active(self) -> bool:
        """Helper to check if the case is currently being worked on."""
        return self.intervention_status not in (
            InterventionStatus.DISMISSED,
            InterventionStatus.EXPIRED,
            InterventionStatus.RESOLVED,
            InterventionStatus.FAILED,
        )

    @property
    def is_open(self) -> bool:
        """Helper to check if the case is open."""
        return self.intervention_status == InterventionStatus.NEW

    @property
    def is_assigned(self) -> bool:
        """Helper to check if the case is open."""
        return (
            self.intervention_status == InterventionStatus.ACCEPTED
            and self.assigned_advisor_id is not None
        )

    def assign_advisor(self, advisor_id: EntityID, occurred_at: datetime) -> None:
        """Assign this case to an advisor."""
        if self.is_assigned:
            raise CaseAlreadyAssignedError(self.case_id)

        self.assigned_advisor_id = advisor_id
        self.assigned_at = occurred_at
        self._transition_to(InterventionStatus.ACCEPTED)

        self.register_event(
            CaseAcceptedEvent(
                case_id=self.case_id,
                advisor_id=advisor_id,
                occurred_at=occurred_at,
            ),
        )

    def mark_as_sent(self) -> None:
        """The intervention email has been sent."""
        self._transition_to(InterventionStatus.SENT)

    def request_email_draft(
        self,
        job_id: EntityID,
        user_id: EntityID,
        booking_link: str | None = None,
    ) -> None:
        """Request an AI-generated email draft for this case."""
        if not self.can_generate_draft():
            raise InvalidStateTransitionError(
                current_status=self.intervention_status.value,
                attempted_action='request_email_draft',
            )

        self.register_event(
            EmailDraftRequestedEvent(
                case_id=self.case_id,
                job_id=job_id,
                user_id=user_id,
                booking_link=booking_link,
            ),
        )

    def record_email_sent(self, job_id: EntityID, user_id: EntityID) -> None:
        """Record that an intervention email has been dispatched."""
        self.mark_as_sent()
        self.register_event(
            InterventionEmailSentEvent(
                case_id=self.case_id,
                job_id=job_id,
                user_id=user_id,
            ),
        )

    def record_booking(
        self,
        appointment_time: datetime,
        meeting_method: MeetingMethod,
        duration_minutes: int = 30,
        notes: str | None = None,
    ) -> None:
        """Student booked an appointment."""
        self._transition_to(InterventionStatus.BOOKED)
        self.appointment = Appointment(
            case_id=self.case_id,
            appointment_time=appointment_time,
            meeting_method=meeting_method,
            duration_minutes=duration_minutes,
            notes=notes,
        )
        self.register_event(
            StudentBookedEvent(
                case_id=self.case_id,
                appointment_time=appointment_time,
                meeting_method=meeting_method,
                notes=notes,
            ),
        )

    def start_supporting(self) -> None:
        """Advisor starts supporting the student after they booked."""
        self._transition_to(InterventionStatus.SUPPORTING)

    def request_resolution(self, occurred_at: datetime) -> None:
        """Mark the case as pending review from the student."""
        self._transition_to(InterventionStatus.PENDING_REVIEW)
        self.register_event(
            CaseReviewRequestedEvent(
                case_id=self.case_id,
                advisor_id=self.assigned_advisor_id,  # type: ignore
                occurred_at=occurred_at,
            ),
        )

    def finalize_resolution(
        self,
        occurred_at: datetime,
        satisfaction: str | None = None,
        comment: str | None = None,
        is_failed: bool = False,
    ) -> None:
        """Mark the case as resolved or failed after review."""
        next_status = (
            InterventionStatus.FAILED if is_failed else InterventionStatus.RESOLVED
        )
        self._transition_to(next_status)
        self.closed_at = occurred_at

        if is_failed:
            self.register_event(
                CaseFailedEvent(
                    case_id=self.case_id,
                    advisor_id=self.assigned_advisor_id,  # type: ignore
                    occurred_at=occurred_at,
                    satisfaction=satisfaction,
                    comment=comment,
                ),
            )
        else:
            self.register_event(
                CaseResolvedEvent(
                    case_id=self.case_id,
                    advisor_id=self.assigned_advisor_id,  # type: ignore
                    occurred_at=occurred_at,
                    satisfaction=satisfaction,
                    comment=comment,
                ),
            )

    def set_ai_overview(self, summary: str, keys: list[str]) -> None:
        """Enrich the case with an AI-generated academic overview."""
        if len(keys) > 3:
            raise ValidationError('Action keys cannot exceed 3 items.')

        self.academic_summary = summary
        self.action_keys = keys

    def _transition_to(self, next_status: InterventionStatus) -> None:
        """The 'Bouncer' that enforces the matrix."""
        if next_status not in _INTERVENTION_STATUS_TRANSITION[self.intervention_status]:
            raise InvalidStateTransitionError(
                current_status=self.intervention_status.value,
                attempted_action=next_status,
            )
        self.intervention_status = next_status

    def can_generate_draft(self) -> bool:
        """Check if this case can perform AI email generation."""
        return self.intervention_status == InterventionStatus.ACCEPTED
