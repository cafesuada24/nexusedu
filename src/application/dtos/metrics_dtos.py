"""Data Transfer Objects for metrics-related operations."""

from dataclasses import dataclass


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
