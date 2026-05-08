"""Case domain entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from src.domain.exceptions import CaseAlreadyAssignedError, InvalidStateTransitionError
from src.domain.value_objects.status import InterventionStatus

_INTERVENTION_STATUS_TRANSITION = {
    InterventionStatus.NEW: [InterventionStatus.ACCEPTED, InterventionStatus.DISMISSED],
    InterventionStatus.ACCEPTED: [
        InterventionStatus.SENT,
        InterventionStatus.DISMISSED,
    ],
    InterventionStatus.SENT: [
        InterventionStatus.BOOKED,
        InterventionStatus.EXPIRED,
        InterventionStatus.DISMISSED,
    ],
    InterventionStatus.BOOKED: [
        InterventionStatus.SUPPORTING,
        InterventionStatus.DISMISSED,
    ],
    InterventionStatus.SUPPORTING: [
        InterventionStatus.RESOLVED,
        InterventionStatus.DISMISSED,
    ],
    # Terminal states have no outgoing transitions
    InterventionStatus.RESOLVED: [],
    InterventionStatus.DISMISSED: [],
    InterventionStatus.EXPIRED: [],
}


@dataclass
class Case:
    """Represents an intervention case for a student."""

    sid: UUID
    case_id: UUID = field(default_factory=uuid4)
    intervention_status: InterventionStatus = InterventionStatus.NEW
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    assigned_at: datetime | None = None
    closed_at: datetime | None = None
    assigned_advisor_id: UUID | None = None
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

    def assign_advisor(self, advisor_id: UUID, occurred_at: datetime) -> None:
        """Assign this case to an advisor."""
        if self.is_assigned:
            raise CaseAlreadyAssignedError(self.case_id)

        self.assigned_advisor_id = advisor_id
        self.assigned_at = occurred_at
        self._transition_to(InterventionStatus.ACCEPTED)

    def mark_as_sent(self) -> None:
        """The intervention email has been sent."""
        self._transition_to(InterventionStatus.SENT)

    def record_booking(self) -> None:
        """Student booked an appointment."""
        self._transition_to(InterventionStatus.BOOKED)

    def resolve(self, occured_at: datetime) -> None:
        """Mark the case as resolved."""
        self._transition_to(InterventionStatus.RESOLVED)
        self.closed_at = occured_at

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
