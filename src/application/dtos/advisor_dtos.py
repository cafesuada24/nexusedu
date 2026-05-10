"""DTOs for advisor-related operations."""

from dataclasses import dataclass
from datetime import date
from typing import Annotated
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    EmailStr,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
)
from pydantic_extra_types.phone_numbers import PhoneNumber, PhoneNumberValidator

# ========== QUERY =========


@dataclass(frozen=True)
class GetUsersAdvisorProfileQuery:
    user_id: UUID


@dataclass(frozen=True)
class GetAdvisorProfileQuery:
    advisor_id: UUID
    include_metrics: bool


@dataclass(frozen=True)
class GetAdvisorAvailabilityQuery:
    advisor_id: UUID
    start_date: date
    end_date: date


class PersonalAdvisorMetricsDTO(BaseModel):
    """Deep personal performance metrics for an advisor."""

    total_points: NonNegativeInt = 0
    total_actions: NonNegativeInt = 0
    total_resolves: NonNegativeInt = 0
    fast_action_count: NonNegativeInt = 0
    avg_response_hours: NonNegativeFloat = 0.0
    recovery_rate: NonNegativeFloat = 0.0


class AdvisorProfileDTO(BaseModel):
    """DTO for an advisor."""

    advisor_id: UUID
    name: str
    email: EmailStr
    title: str | None = Field(default=None)
    phone: (
        Annotated[PhoneNumber | str, PhoneNumberValidator(number_format='E164')] | None
    ) = None
    faculty: str | None = None
    office: str | None = None
    bio: str | None = None

    personal_metrics: PersonalAdvisorMetricsDTO | None = None


class AvailabilitySlotDTO(BaseModel):
    """DTO for an available appointment slot."""

    start_time: AwareDatetime
    end_time: AwareDatetime


@dataclass(frozen=True)
class BadgeDTO:
    """DTO for an achievement badge."""

    badge_id: str
    name: str
    description: str
    icon: str
