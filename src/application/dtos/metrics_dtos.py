"""Data Transfer Objects for metrics-related operations."""

from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, Field, NonNegativeFloat, NonNegativeInt, PositiveInt


@dataclass
class KPIStatsDTO:
    """DTO for high-level KPI stats."""

    retention_rate: float
    total_interventions: int
    advisor_engagement: float
    dropout_rate: float
    total_students: int


@dataclass
class RetentionTrendDTO:
    """DTO for retention trend data point."""

    month: str
    baseline: int
    current: float


class ResponseKpiMetricDTO(BaseModel):
    """DTO for Response KPI metrics."""

    avg_response_hours: NonNegativeFloat
    target_hours: NonNegativeFloat = 4.0

    within_kpi_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    sla_breach_count: NonNegativeInt


class RecoveryMetricDTO(BaseModel):
    """DTO for student recovery metrics."""

    recovery_rate: float

    stabilized_students: int
    total_risk_students: int

    avg_recovery_days: float


class ImpactHistoryDTO(BaseModel):
    """DTO for weekly XP history."""

    week: PositiveInt
    xp: NonNegativeInt


class ImpactMetricDTO(BaseModel):
    """DTO for advisor impact metrics."""

    current_xp: int

    completion_rate: float

    ranking_position: int | None = None

    month: PositiveInt
    year: PositiveInt

    weekly_history: list[ImpactHistoryDTO]


class EmergencyDashboardDTO(BaseModel):
    """Aggregate DTO for the Advisor Emergency Dashboard."""

    priority_queue: NonNegativeInt

    response_kpi: ResponseKpiMetricDTO

    activation: Annotated[float, Field(ge=0.0, le=1.0)]

    recovery: RecoveryMetricDTO

    impact: ImpactMetricDTO
