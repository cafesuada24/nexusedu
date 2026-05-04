from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.value_objects.status import (
    InterventionStatus,
    RiskStatus,
    TaskStatus,
    TaskType,
)


@dataclass
class TaskDTO:
    """DTO for a task associated with a case."""

    task_id: UUID
    action_type: TaskType
    status: TaskStatus
    points_reward: int
    completed_at: datetime | None
    completed_by_advisor_id: UUID | None


@dataclass
class CaseDTO:
    """DTO for a case in the advisor case list."""

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
    draft_status: str | None
    assigned_to: str | None
    suggested_action: str
    points_reward: int
    tasks: list[TaskDTO] | None = None
