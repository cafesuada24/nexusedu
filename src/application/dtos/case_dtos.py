from dataclasses import dataclass
from datetime import datetime

from pydantic import AwareDatetime, BaseModel, EmailStr, FutureDatetime

from src.core.identifiers import EntityID
from src.domain.value_objects.status import (
    EmailStatus,
    InterventionStatus,
    JobStatus,
    MeetingMethod,
    RiskStatus,
)
from src.domain.value_objects.student_satisfaction import StudentSatisfaction


@dataclass
class AcceptCaseCommand:
    """Command to complete a task and award points."""

    case_id: EntityID
    user_id: EntityID
    accepted_at: datetime


@dataclass
class TriggerDraftCommand:
    """Command to trigger a background email draft generation."""

    case_id: EntityID
    user_id: EntityID


@dataclass
class GenerateEmailDraftCommand:
    """Command to generate an email draft (intended for worker)."""

    case_id: EntityID
    job_id: EntityID
    user_id: EntityID | None = None


@dataclass
class SendEmailCommand:
    """Command to record and send an intervention email."""

    case_id: EntityID
    user_id: EntityID


@dataclass
class UpdateEmailCommand:
    """Command to manually update an email draft."""

    case_id: EntityID
    user_id: EntityID
    subject: str | None = None
    body: str | None = None


@dataclass(frozen=True)
class BookAppointmentCommand:
    """Command to record a student booking an appointment."""

    case_id: EntityID
    appointment_time: FutureDatetime
    meeting_method: MeetingMethod
    duration_minutes: int = 30
    notes: str | None = None


@dataclass(frozen=True)
class StartSupportingCommand:
    """Command for an advisor to start supporting a case."""

    case_id: EntityID
    user_id: EntityID


@dataclass(frozen=True)
class ResolveCaseCommand:
    """Command for an advisor to resolve a case."""

    case_id: EntityID
    user_id: EntityID


@dataclass(frozen=True)
class SubmitCaseReviewCommand:
    """Command to submit a student review and finalize the case."""

    case_id: EntityID
    satisfaction: StudentSatisfaction
    comment: str | None = None


@dataclass(frozen=True)
class GetAssignedQuery:
    """Query to retrieve advisor task list."""

    user_id: EntityID
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class GetUnassignedQuery:
    """Query to retrieve advisor task list."""

    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class GetAllCasesQuery:
    """Query to retrieve all cases (Admin only)."""

    user_id: EntityID
    limit: int = 20
    offset: int = 0


# ==========================
# ========== DTOs ==========
# ==========================


class TriggerDraftDTO(BaseModel):
    job_id: EntityID
    status: JobStatus
    is_new_job: bool


class SendEmailResponseDTO(BaseModel):
    """Response for the send email action, allowing job tracking."""

    job_id: EntityID
    status: JobStatus
    recipient: EmailStr


class ActionResponseDTO(BaseModel):
    """Generic response for status updates and actions."""

    status: str
    message: str


class ReviewCaseDTO(BaseModel):
    """Schema for submitting a student review."""

    satisfaction: StudentSatisfaction
    comment: str | None = None


class QueryEmailDTO(BaseModel):
    email_id: EntityID

    recipent: EmailStr
    subject: str | None = None
    body: str | None = None
    status: EmailStatus
    created_at: datetime
    sent_at: datetime | None = None

class QueryAppointmentDTO(BaseModel):
    appointment_time: AwareDatetime
    duration_minutes: int
    meeting_method: MeetingMethod
    notes: str | None

class CaseOverviewDTO(BaseModel):
    """DTO for AI-generated academic overview of a case."""

    academic_summary: str
    action_keys: list[str]

class CaseDTO(BaseModel):
    """Schema for a student case."""

    case_id: EntityID
    sid: EntityID
    created_at: AwareDatetime

    assigned_advisor_id: EntityID | None
    assigned_to: str | None

    student_name: str
    major: str

    current_risk_status: RiskStatus
    intervention_status: InterventionStatus

    email: QueryEmailDTO | None
    appointment: QueryAppointmentDTO | None = None
    ai_overview: CaseOverviewDTO | None = None
