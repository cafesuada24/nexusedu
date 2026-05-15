"""Data Transfer Objects for the Application layer."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, NonNegativeFloat

from src.core.identifiers import EntityID
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

    sid: EntityID


@dataclass(frozen=True)
class GetStudentTermMetricsQuery:
    """Query to retrieve term metrics for a single student."""

    sid: EntityID
    academic_year: int | None = None
    semester: int | None = None


class StudentDTO(BaseModel):
    """DTO for student data."""

    sid: EntityID
    student_name: str
    email: str
    major: str
    current_risk_status: RiskStatus
    intervention_status: InterventionStatus | None = None
    last_notified_at: datetime | None
    is_generating: bool = False
    active_case_id: EntityID | None = None
    
    # Adaptive Evaluation Signals
    current_trend: float | None = None
    confidence_score: float | None = None
    is_systemic: bool = False


class AlertDTO(BaseModel):
    """DTO for alert data."""

    student: StudentDTO
    alert_details: dict[str, Any]


class TermCourseMetricsDTO(BaseModel):
    """DTO for course metrics in a term."""

    course_id: str
    course_name: str
    avg_score: NonNegativeFloat


class TermMetricsDTO(BaseModel):
    """DTO for student performance in a specific term."""

    academic_year: int
    semester: int
    term_avg_score: float
    previous_terms_avg_score: float | None
    courses: list[TermCourseMetricsDTO]


class StudentTermMetricsDTO(BaseModel):
    """DTO for student term metrics response."""

    sid: EntityID
    terms: list[TermMetricsDTO]
