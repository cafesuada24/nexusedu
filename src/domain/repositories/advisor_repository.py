"""Advisor repository interface."""

from typing import Any, Protocol
from uuid import UUID

from src.domain.entities.advisor import Advisor


class AdvisorRepository(Protocol):
    """Interface for advisor-related data operations."""

    async def get_by_id(self, advisor_id: UUID) -> Advisor | None:
        """Retrieve an advisor by their unique ID."""
        ...

    async def get_engagement_metrics(self) -> list[dict[str, Any]]:
        """Retrieve aggregated engagement metrics by major."""
        ...

    async def get_leaderboard(
        self,
        time_window: str,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Retrieve the advisor leaderboard for a specific time window with pagination.
        
        Returns:
            Tuple of (list of leaderboard entries, total count)
        """
        ...

    async def record_points(
        self,
        advisor_id: UUID,
        sid: UUID,
        action_type: str,
        points: int,
    ) -> None:
        """Record gamification points for an advisor action."""
        ...

    async def has_existing_action(
        self, advisor_id: UUID, sid: UUID, action_type: str
    ) -> bool:
        """Check if an action has already been recorded for this advisor/student combination."""
        ...
