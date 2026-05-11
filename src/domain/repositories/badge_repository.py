"""Badge repository interface."""

from typing import Protocol

from src.core.identifiers import EntityID


class BadgeRepository(Protocol):
    """Interface for achievement badge data operations."""

    async def get_advisor_badges(self, advisor_id: EntityID) -> list[str]:
        """Retrieve a list of badge IDs earned by the advisor."""
        ...

    async def award_badge(self, advisor_id: EntityID, badge_id: str) -> bool:
        """Award a badge to an advisor.

        Returns:
            bool: True if badge was newly awarded, False if already had it.
        """
        ...

    async def get_advisor_stats(self, advisor_id: EntityID) -> dict:
        """Get aggregated stats to evaluate badge criteria.

        Returns a dict with:
            total_points: int
            fast_action_count: int
            avg_response_hours: float
            total_actions: int
            recovery_rate: float
            total_resolves: int
        """
        ...
