"""DTOs for advisor-related operations."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class EngagementMetricsDTO:
    """DTO for aggregated engagement metrics."""

    major: str
    sent_count: int
    drafted_count: int


@dataclass(frozen=True)
class LeaderboardEntryDTO:
    """DTO for a single leaderboard entry."""

    advisor_id: UUID
    name: str
    total_points: int
    actions_count: int
    sent_count: int
    resolved_count: int


@dataclass(frozen=True)
class BadgeDTO:
    """DTO for an achievement badge."""

    badge_id: str
    name: str
    description: str
    icon: str
