"""Case domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.value_objects.status import CaseStatus, EmailStatus, InterventionStatus, RiskStatus


@dataclass
class Case:
    """Represents an intervention case for a student."""

    case_id: UUID = field(default_factory=uuid4)
    sid: UUID = field(default_factory=uuid4)
    status: CaseStatus = CaseStatus.OPEN
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: datetime | None = None
    assigned_advisor_id: UUID | None = None


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
