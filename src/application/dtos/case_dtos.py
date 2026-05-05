from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, EmailStr

from src.domain.value_objects.status import (
    InterventionStatus,
    RiskStatus,
    TaskStatus,
    TaskType,
)


@dataclass(frozen=True)
class TaskDTO:
    """DTO for a task associated with a case."""

    task_id: UUID
    action_type: TaskType
    status: TaskStatus
    points_reward: int
    completed_at: datetime | None
    completed_by_advisor_id: UUID | None


class CaseDTO(BaseModel):
    """Schema for a student case."""

    case_id: UUID
    sid: UUID
    created_at: AwareDatetime

    assigned_advisor_id: UUID | None
    assigned_to: str | None

    student_name: str
    major: str

    current_risk_status: RiskStatus
    intervention_status: InterventionStatus

    email: EmailStr
    draft_subject: str | None
    draft_body: str | None
    draft_status: str

    points_reward: int

