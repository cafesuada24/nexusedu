"""Data Transfer Objects for the Application layer."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import UUID4

from src.domain.value_objects.status import InterventionStatus, RiskStatus


@dataclass
class StudentDTO:
    """DTO for student data."""

    sid: UUID4
    student_name: str | None
    email: str | None
    major: str
    current_risk_status: RiskStatus
    intervention_status: InterventionStatus
    last_notified_at: datetime
    is_generating: bool = False
    active_case_id: UUID4 | None = None


@dataclass
class AlertDTO:
    """DTO for alert data."""

    student: StudentDTO
    alert_details: dict[str, Any]


@dataclass
class EmailDTO:
    """DTO for intervention email data."""

    email_id: UUID
    sid: UUID
    subject: str | None
    body: str | None
    status: str
    created_at: str
    sent_at: str | None = None


@dataclass
class TaskDTO:
    """DTO for a task in the advisor task list."""

    case_id: UUID
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
