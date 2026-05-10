"""Data Transfer Objects for the Application layer."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import UUID4, BaseModel

from src.domain.value_objects.status import InterventionStatus, RiskStatus


@dataclass(frozen=True)
class GetAllStudentsQuery:
    """Query to retrieve all students."""

    limit: int = 20
    offset: int = 0
    risk_status: RiskStatus | None = None


@dataclass(frozen=True)
class GetStudentQuery:
    """Query to retrieve a single student."""

    sid: UUID


class StudentDTO(BaseModel):
    """DTO for student data."""

    sid: UUID4
    student_name: str | None
    email: str | None
    major: str
    current_risk_status: RiskStatus
    intervention_status: InterventionStatus | None = None
    last_notified_at: datetime | None
    is_generating: bool = False
    active_case_id: UUID4 | None = None


class AlertDTO(BaseModel):
    """DTO for alert data."""

    student: StudentDTO
    alert_details: dict[str, Any]
