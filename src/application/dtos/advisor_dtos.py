"""DTOs for advisor-related operations."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, PositiveInt
from pydantic_extra_types.phone_numbers import PhoneNumber, PhoneNumberValidator

# ========== QUERY =========


@dataclass(frozen=True)
class GetLeaderboardQuery:
    """Query to retrieve the advisor leaderboard."""

    time_window: str
    limit: int = 10
    offset: int = 0


# @dataclass(frozen=)


@dataclass(frozen=True)
class GetUsersAdvisorProfileQuery:
    user_id: UUID


@dataclass(frozen=True)
class GetAdvisorProfileQuery:
    advisor_id: UUID
    include_metrics: bool


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


class AdvisorMetricsDTO(BaseModel):
    points: PositiveInt = 0


class AdvisorProfileDTO(BaseModel):
    """DTO for an advisor."""

    advisor_id: UUID
    name: str
    email: EmailStr
    title: str | None = Field(default=None)
    phone: str | None = None
    faculty: str | None = None
    office: str | None = None
    bio: str | None = None

    metrics: AdvisorMetricsDTO | None = None


@dataclass(frozen=True)
class BadgeDTO:
    """DTO for an achievement badge."""

    badge_id: str
    name: str
    description: str
    icon: str
