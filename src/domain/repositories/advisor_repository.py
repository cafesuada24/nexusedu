"""Advisor repository interface."""

from typing import Any, Protocol
from uuid import UUID

from src.domain.entities.advisor import Advisor


class AdvisorRepository(Protocol):
    """Interface for advisor-related data operations."""

    async def get_by_id(self, advisor_id: UUID) -> Advisor | None:
        """Retrieve an advisor by their unique ID."""
        ...

    async def get_by_user_id(self, user_id: UUID) -> Advisor | None:
        """Retrieve an advisor by their associated user ID."""
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
        task_id: UUID,
        points: int,
    ) -> None:
        """Record gamification points for a completed task."""
        ...

    async def has_existing_reward(self, advisor_id: UUID, task_id: UUID) -> bool:
        """Check if a reward has already been recorded for this advisor/task combination."""
        ...

    async def upsert_advisor_for_user(
        self,
        user_id: UUID,
        email: str,
        name: str,
    ) -> None:
        """Link a user to an advisor profile, creating one if necessary."""
        ...

    async def get_advisor_points(self, advisor_id: UUID) -> int:
        """Get total points for an advisor."""
        ...
