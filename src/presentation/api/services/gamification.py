"""Service for handling gamification and advisor rewards."""

import datetime
from typing import TYPE_CHECKING

from src.domain.repositories.interfaces import AdvisorRepository, StudentRepository


class GamificationService:
    """Service for managing advisor points and SLAs."""

    def __init__(
        self,
        advisor_repo: AdvisorRepository,
        student_repo: StudentRepository,
    ) -> None:
        """Initialize the service with necessary repositories."""
        self.advisor_repo = advisor_repo
        self.student_repo = student_repo

    async def award_points(self, advisor_id: str, sid: str, action_type: str) -> int:
        """Calculate and award points for an advisor action."""
        matrix = {
            'draft_reviewed': 5,
            'email_sent': 10,
            'meeting_booked': 50,
            'student_resolved': 100,
        }
        base_points = matrix.get(action_type, 0)
        if base_points == 0:
            return 0

        # Calculate multiplier based on 24h SLA
        multiplier = 1.0
        recorded_dt = await self.student_repo.get_latest_status_timestamp(sid)

        if recorded_dt:
            now = datetime.datetime.now(datetime.UTC)
            # Ensure recorded_dt is timezone-aware if it's not
            if recorded_dt.tzinfo is None:
                recorded_dt = recorded_dt.replace(tzinfo=datetime.UTC)

            # 24h SLA in seconds
            sla_24h = 86400
            if (now - recorded_dt).total_seconds() < sla_24h:
                multiplier = 1.2

        final_points = int(base_points * multiplier)
        await self.advisor_repo.record_points(
            advisor_id, sid, action_type, final_points
        )
        return final_points
