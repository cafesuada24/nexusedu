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

    async def get_leaderboard(self, time_window: str) -> list[dict[str, Any]]:
        """Retrieve the advisor leaderboard for a specific time window."""
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
