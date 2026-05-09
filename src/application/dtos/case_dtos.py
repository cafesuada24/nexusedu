from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, EmailStr

from src.domain.value_objects.status import (
    EmailStatus,
    InterventionStatus,
    JobStatus,
    RiskStatus,
)


@dataclass
class AcceptCaseCommand:
    """Command to complete a task and award points."""

    case_id: UUID
    user_id: UUID
    accepted_at: datetime


@dataclass
class TriggerDraftCommand:
    """Command to trigger a background email draft generation."""

    case_id: UUID
    user_id: UUID
    booking_link: str | None = None


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


@dataclass
class UpdateEmailCommand:
    """Command to manually update an email draft."""

    case_id: UUID
    user_id: UUID
    subject: str | None = None
    body: str | None = None


@dataclass(frozen=True)
class BookAppointmentCommand:
    """Command to record a student booking an appointment."""

    case_id: UUID


@dataclass(frozen=True)
class StartSupportingCommand:
    """Command for an advisor to start supporting a case."""

    case_id: UUID
    user_id: UUID


@dataclass(frozen=True)
class ResolveCaseCommand:
    """Command for an advisor to resolve a case."""

    case_id: UUID
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


# ==========================
# ========== DTOs ==========
# ==========================


class TriggerDraftDTO(BaseModel):
    job_id: UUID
    status: JobStatus
    is_new_job: bool


class ActionResponseDTO(BaseModel):
    """Generic response for status updates and actions."""

    status: str
    message: str


class QueryEmailDTO(BaseModel):
    email_id: UUID

    recipent: EmailStr
    subject: str | None = None
    body: str | None = None
    status: EmailStatus
    created_at: datetime
    sent_at: datetime | None = None

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

    email: QueryEmailDTO | None
