from uuid import UUID

from pydantic import BaseModel, NonNegativeInt, PositiveInt

from src.domain.value_objects.gamification import RankingType


class GetLeaderboardQuery(BaseModel):
    """Query to retrieve the advisor leaderboard."""

    time_window: RankingType
    limit: PositiveInt = 10
    offset: NonNegativeInt = 0


class LeaderboardEntryDTO(BaseModel):
    """DTO for a single leaderboard entry."""

    advisor_id: UUID
    name: str
    total_points: NonNegativeInt
    actions_count: NonNegativeInt
    sent_count: NonNegativeInt
    resolved_count: NonNegativeInt
