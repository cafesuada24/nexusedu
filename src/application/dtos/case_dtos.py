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


@dataclass
class AcceptCaseCommand:
    """Command to complete a task and award points."""

    case_id: UUID
    user_id: UUID
    accepted_at: datetime


@dataclass
class UpdateStudentStatusCommand:
    """Command to update a student's intervention status."""

    case_id: UUID
    status: InterventionStatus
    user_id: UUID


@dataclass
class AwardReviewPointsCommand:
    """Command to award points for reviewing a draft."""

    case_id: UUID
    user_id: UUID


@dataclass
class TriggerDraftCommand:
    """Command to trigger a background email draft generation."""

    case_id: UUID
    user_id: UUID
    booking_link: str | None = None
    update_db: bool = True


@dataclass
class GenerateEmailDraftCommand:
    """Command to generate an email draft (intended for worker)."""

    case_id: UUID
    job_id: UUID
    booking_link: str | None = None
    user_id: UUID | None = None


@dataclass
class SendEmailCommand:
    """Command to record and send an intervention email."""

    case_id: UUID
    body: str
    user_id: UUID

@dataclass(frozen=True)
class GetAssignedQuery:
    """Query to retrieve advisor task list."""

    user_id: UUID
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class GetUnassignedQuery:
    """Query to retrieve advisor task list."""

    limit: int = 20
    offset: int = 0


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
    draft_status: str | None

    points_reward: int
