"""DTOs for the Admin Dashboard."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RecoveryMetricDTO(BaseModel):
    """Metric for student recovery rate."""

    recovery_rate: float = Field(..., ge=0.0, le=1.0)
    stabilized_students: int
    total_at_risk_students: int


class LeadTimeMetricDTO(BaseModel):
    """Metric for intervention response lead time."""

    avg_lead_time_hours: float
    target_hours: float = 4.0
    within_target_rate: float = Field(..., ge=0.0, le=1.0)


class NudgeActivationMetricDTO(BaseModel):
    """Metric for nudge effectiveness."""

    activation_rate: float = Field(..., ge=0.0, le=1.0)
    total_nudges_sent: int
    responses_received: int


class AcademicImpactMetricDTO(BaseModel):
    """Metric for academic improvement after intervention."""

    avg_gpa_before: float | None
    avg_gpa_after: float | None
    impact_score: float | None


class RiskDistributionDTO(BaseModel):
    """Distribution of risk reasons."""

    label: str
    count: int
    percentage: float


class MajorRiskMetricDTO(BaseModel):
    """Risk percentage per major."""

    major: str
    risk_percentage: float
    total_students: int


class SystemicRiskMetricDTO(BaseModel):
    """Metric for school-wide breadth of risk."""

    avg_breadth: float = Field(..., ge=0.0, le=1.0)
    systemic_case_count: int


class TrendDistributionDTO(BaseModel):
    """Metric for overall direction of student performance."""

    improving: int
    stable: int
    declining: int


class AdvisorAdminMetricRowDTO(BaseModel):
    """Detailed performance metrics for a single advisor."""

    advisor_id: UUID
    name: str
    faculty: str | None
    active_cases: int
    total_cases: int
    avg_resolution_days: float | None
    avg_lead_time_hours: float | None
    meeting_hours: float
    outreach_success_rate: float
    recovery_rate: float


class AdvisorAdminMetricsResponseDTO(BaseModel):
    """Aggregate DTO for advisor performance metrics."""

    advisors: list[AdvisorAdminMetricRowDTO]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class AdminDashboardDTO(BaseModel):
    """Aggregate DTO for the Admin Dashboard."""

    recovery: RecoveryMetricDTO
    lead_time: LeadTimeMetricDTO
    nudge_activation: NudgeActivationMetricDTO
    academic_impact: AcademicImpactMetricDTO
    risk_distribution: list[RiskDistributionDTO]
    major_risk: list[MajorRiskMetricDTO]
    systemic_risk: SystemicRiskMetricDTO | None = None
    trend_distribution: TrendDistributionDTO | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
