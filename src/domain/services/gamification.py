"""Domain service for handling gamification and advisor rewards."""

import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.value_objects.status import RiskStatus


class GamificationService:
    """Service for managing advisor points and SLAs."""

    DEFAULT_MATRIX = {
        'draft_reviewed': 5,
        'email_sent': 10,
        'meeting_booked': 50,
        'student_resolved': 100,
    }

    def __init__(self, matrix: dict[str, int] | None = None) -> None:
        """Initialize with an optional custom scoring matrix."""
        self.matrix = matrix or self.DEFAULT_MATRIX

    def calculate_points(
        self,
        action_type: str,
        recorded_dt: datetime.datetime | None,
        risk_level: 'RiskStatus | None' = None,
    ) -> int:
        """Calculate points for an advisor action."""
        base_points = self.matrix.get(action_type, 0)
        if base_points == 0:
            return 0

        # Risk multiplier
        risk_multiplier = 0.3
        if risk_level:
            risk_multiplier = {
                'Critical': 1.0,
                'Elevated': 0.7,
                'Normal': 0.3,
                'Unknown': 0.3,
            }.get(str(risk_level).split('.')[-1], 0.3)

        points_after_risk = base_points * risk_multiplier

        if recorded_dt is None:
            return int(points_after_risk)

        # Calculate multiplier based on 24h SLA
        multiplier = 1.0

        now = datetime.datetime.now(datetime.UTC)
        # Ensure recorded_dt is timezone-aware if it's not
        if recorded_dt.tzinfo is None:
            recorded_dt = recorded_dt.replace(tzinfo=datetime.UTC)

        # 24h SLA in seconds
        sla_24h = 86400
        if (now - recorded_dt).total_seconds() < sla_24h:
            multiplier = 1.2

        return int(base_points * multiplier)
