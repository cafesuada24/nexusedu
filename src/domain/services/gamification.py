"""Domain service for handling gamification and advisor rewards."""

import datetime

from src.domain.value_objects.status import RiskStatus


class GamificationService:
    """Service for managing advisor points and SLAs."""

    DEFAULT_MATRIX = {
        'draft_reviewed': 5,
        'email_sent': 10,
        'meeting_booked': 50,
        'student_resolved': 100,
    }

    RISK_MULTIPLIERS: dict[RiskStatus, float] = {
        RiskStatus.CRITICAL: 1.0,
        RiskStatus.ELEVATED: 0.7,
        RiskStatus.NORMAL: 0.3,
        RiskStatus.UNKNOWN: 0.3,
    }

    def __init__(self, matrix: dict[str, int] | None = None) -> None:
        """Initialize with an optional custom scoring matrix."""
        self.matrix = matrix or self.DEFAULT_MATRIX

    def calculate_points(
        self,
        action_type: str,
        recorded_dt: datetime.datetime | None,
        risk_level: RiskStatus = RiskStatus.UNKNOWN,
    ) -> int:
        """Calculate points for an advisor action.

        Args:
            action_type: The gamified action (e.g. 'draft_reviewed').
            recorded_dt: Timestamp of the student's last status recording.
            risk_level: The student's current risk status for weighting.

        Returns:
            Calculated integer points after risk and SLA multipliers.
        """
        base_points = self.matrix.get(action_type, 0)
        if base_points == 0:
            return 0

        # Risk multiplier
        risk_multiplier = self.RISK_MULTIPLIERS.get(risk_level, 0.3)
        points_after_risk = base_points * risk_multiplier

        if recorded_dt is None:
            return int(points_after_risk)

        # Tiered SLA multiplier (12h / 24h / 72h)
        now = datetime.datetime.now(datetime.UTC)
        if recorded_dt.tzinfo is None:
            recorded_dt = recorded_dt.replace(tzinfo=datetime.UTC)

        delta_seconds = (now - recorded_dt).total_seconds()

        if delta_seconds < 12 * 3600:
            sla_multiplier = 1.5
        elif delta_seconds < 24 * 3600:
            sla_multiplier = 1.2
        elif delta_seconds < 72 * 3600:
            sla_multiplier = 1.0
        else:
            sla_multiplier = 0.8  # Penalty for taking longer than 72h

        return int(points_after_risk * sla_multiplier)
