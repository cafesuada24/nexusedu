"""Case domain entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from src.application.exceptions import InvalidStatusTransitionError
from src.domain.entities.task import Task
from src.domain.exceptions import CaseAlreadyAssignedError
from src.domain.value_objects.status import (
    CaseStatus,
    EmailStatus,
    InterventionStatus,
    RiskStatus,
)


@dataclass
class Case:
    """Represents an intervention case for a student."""

    risk_status: RiskStatus
    sid: UUID
    case_id: UUID = field(default_factory=uuid4)
    status: CaseStatus = CaseStatus.OPEN
    created_at: datetime = field(default_factory=datetime.now)
    assigned_at: datetime | None = None
    closed_at: datetime | None = None
    assigned_advisor_id: UUID | None = None
    tasks: list[Task] = field(default_factory=list[Task])
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
        return self.status == CaseStatus.ASSIGNED

    def assign_advisor(self, advisor_id: UUID, occurred_at: datetime) -> None:
        """Assign this case to an advisor."""
        if self.assigned_advisor_id is not None:
            raise CaseAlreadyAssignedError(self.case_id)

        self.assigned_advisor_id = advisor_id
        self.assigned_at = occurred_at
        self.__transition_to(new_status=CaseStatus.ASSIGNED, occurred_at=occurred_at)

    def __transition_to(self, new_status: CaseStatus, occurred_at: datetime) -> None:
        """Perform case status transistion."""
        if new_status == CaseStatus.RESOLVED and self.assigned_advisor_id is None:
            raise InvalidStatusTransitionError('Cannot resolve unassigned case.')

        self.status = new_status

        if new_status in (CaseStatus.FAILED, CaseStatus.RESOLVED):
            self.closed_at = occurred_at

    def resolve(self, occured_at: datetime) -> None:
        """Mark the case as resolved."""
        self.__transition_to(CaseStatus.RESOLVED, occurred_at=occured_at)

    def fail(self, occured_at: datetime) -> None:
        """Mark this case as failed."""
        self.__transition_to(CaseStatus.FAILED, occurred_at=occured_at)


@dataclass
class TaskItemRecord:
    """Represents a task for an advisor."""

    case_id: UUID
    sid: UUID
    created_at: datetime
    assigned_advisor_id: UUID | None
    student_name: str | None
    email: str | None
    major: str
    current_risk_status: RiskStatus
    intervention_status: InterventionStatus
    draft_subject: str | None
    draft_body: str | None
    draft_status: EmailStatus | str | None
    assigned_to: str | None
    suggested_action: str
    tasks: list[Task] = field(default_factory=list[Task])
