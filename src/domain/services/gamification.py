"""Domain service for handling gamification and advisor rewards."""

import datetime
from enum import StrEnum

from src.domain.value_objects.status import RiskStatus


class GamificationService:
    """Service for managing advisor points and SLAs."""

    class Action(StrEnum):
        ACCEPT_TASK = 'accept_task'
        SEND_EMAIL = 'send_email'
        STUDENT_BOOK = 'student_book'
        RESOLVE_CASE = 'resolve_case'

    DEFAULT_MATRIX = {
        Action.ACCEPT_TASK: 5,
        # 'review draft': 5,
        Action.SEND_EMAIL: 10,
        Action.STUDENT_BOOK: 50,
        Action.RESOLVE_CASE: 100,
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
        action_type: Action,
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

    def check_badges(self, advisor_stats: dict) -> list[str]:
        """Check which badges the advisor qualifies for based on their stats.

        Expected stats dict:
            total_points: int
            fast_action_count: int
            avg_response_hours: float
            total_actions: int
            recovery_rate: float
            total_resolves: int
        """
        earned_badges = []

        total_points = advisor_stats.get('total_points', 0)
        fast_action_count = advisor_stats.get('fast_action_count', 0)
        avg_response_hours = advisor_stats.get('avg_response_hours', 999.0)
        total_actions = advisor_stats.get('total_actions', 0)
        recovery_rate = advisor_stats.get('recovery_rate', 0.0)
        total_resolves = advisor_stats.get('total_resolves', 0)

        if fast_action_count >= 3:
            earned_badges.append('speed_demon')

        if total_points >= 100:
            earned_badges.append('century_club')

        if total_points >= 500:
            earned_badges.append('five_hundred')

        if total_actions >= 5 and avg_response_hours < 4.0:
            earned_badges.append('fastest_avg_response')

        if total_resolves >= 5 and recovery_rate > 0.8:
            earned_badges.append('highest_recovery_rate')

        return earned_badges

