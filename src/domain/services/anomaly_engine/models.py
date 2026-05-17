"""Internal data models for the anomaly engine."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.services.anomaly_engine.domain_mapper import CourseDomain
from src.domain.value_objects.status import RiskStatus


class ActivityMeasurement(BaseModel):
    """Input measurement for a single student activity."""
    model_config = ConfigDict(frozen=True)

    sid: UUID
    course_id: str
    course_name: str | None = None
    academic_year: int
    semester: int
    week: int
    score: float
    course_avg: float
    course_std: float
    domain: CourseDomain = CourseDomain.OTHER

    @field_validator('score', 'course_avg', 'course_std')
    @classmethod
    def validate_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Values must be finite (not NaN or Inf)")
        return v



class StudentDomainProfile(BaseModel):
    """Adaptive historical profile for a student in a specific domain."""
    model_config = ConfigDict(validate_assignment=True)

    domain: CourseDomain
    ewma_z_peer: float = 0.0  # Adaptive baseline (EWMA of historical z-peers)
    ewma_variance: float = 1.0  # Adaptive volatility (EWMA of squared deviations)
    ewma_drift: float = 0.0   # Adaptive trend (EWMA of historical drifts)
    observation_count: int = 0
    last_updated_at: datetime | None = None

    @property
    def volatility(self) -> float:
        """Returns the current adaptive standard deviation."""
        return math.sqrt(self.ewma_variance)

    def update(self, z_peer: float, alpha: float = 0.3, gamma: float = 0.2) -> None:
        """Update adaptive baseline, volatility, and trend with a new observation."""
        if self.observation_count == 0:
            self.ewma_z_peer = z_peer
            self.ewma_variance = 1.0  # Default initial variance
            self.ewma_drift = 0.0
        else:
            # 1. Calculate drift from prior baseline
            drift = z_peer - self.ewma_z_peer

            # 2. Update Baseline Mean
            self.ewma_z_peer = (alpha * z_peer) + ((1 - alpha) * self.ewma_z_peer)

            # 3. Update Baseline Volatility (EWMA Variance)
            # Use squared deviation from the PRIOR mean for variance estimate
            # (Standard EWMA variance formula)
            squared_dev = drift**2
            self.ewma_variance = (alpha * squared_dev) + ((1 - alpha) * self.ewma_variance)

            # 4. Update Trend (longer-memory EWMA of drifts)
            self.ewma_drift = (gamma * drift) + ((1 - gamma) * self.ewma_drift)

        self.observation_count += 1
        self.last_updated_at = datetime.now(UTC)


class EvaluationResult(BaseModel):
    """Output of the evaluation engine for a specific week."""
    model_config = ConfigDict(frozen=True)

    sid: UUID
    academic_year: int
    semester: int
    week: int

    # Statistical signals
    avg_score: float
    avg_z_peer: float         # Mean performance relative to peers
    avg_drift: float          # Deviation from personal adaptive baseline
    avg_normalized_drift: float  # Drift normalized by volatility (p-signal)
    trend_score: float        # Multi-week trend signal (EWMA of drifts)
    confidence: float         # Statistical confidence (0.0 to 1.0)
    systemic_breadth: float   # Ratio of domains showing negative drift (0.0 to 1.0)

    # Classification
    risk_status: RiskStatus
    is_anomaly: bool = False

    # Metadata for persistence/debugging
    metadata: dict[str, float | str] = Field(default_factory=dict)


EvaluationResult.model_rebuild()
