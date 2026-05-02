"""Domain service for handling gamification and advisor rewards."""

import datetime


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
        self, action_type: str, recorded_dt: datetime.datetime | None
    ) -> int:
        """Calculate points for an advisor action."""
        base_points = self.matrix.get(action_type, 0)
        if base_points == 0:
            return 0


        if recorded_dt is None:
            return base_points

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
