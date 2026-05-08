"""Gamification query service interface."""

from typing import Protocol

from src.application.dtos.gamification_dtos import (
    EngagementMetricsEntryDTO,
    LeaderboardEntryDTO,
)
from src.application.dtos.pagination import PagedResponse
from src.domain.value_objects.gamification import RankingType


class GamificationQueryService(Protocol):
    """Gamification query service interface."""

    async def get_leader_board(
        self,
        time_window: RankingType,
        limit: int = 10,
        offset: int = 0,
    ) -> PagedResponse[LeaderboardEntryDTO]:
        """Get the current leaderboard."""
        ...

    async def get_engagement_metrics(self) -> list[EngagementMetricsEntryDTO]:
        """Retrieve aggregated engagement metrics by major."""
        ...
