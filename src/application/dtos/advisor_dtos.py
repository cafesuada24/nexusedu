"""DTOs for advisor-related operations."""

from dataclasses import dataclass
from datetime import date, time
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


@dataclass(frozen=True)
class GetAdvisorScheduleQuery:
    advisor_id: UUID

@dataclass(frozen=True)
class GetUserAdvisorScheduleQuery:
    user_id: UUID


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


class WorkingHoursDTO(BaseModel):
    """DTO for a working hour block."""

    id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    timezone: str


class DayOffDTO(BaseModel):
    """DTO for a day off."""

    id: UUID
    date: date
    reason: str | None = None


class AdvisorScheduleDTO(BaseModel):
    """DTO for a combined advisor schedule."""

    working_hours: list[WorkingHoursDTO]
    days_off: list[DayOffDTO]


@dataclass(frozen=True)
class BadgeDTO:
    """DTO for an achievement badge."""

    badge_id: str
    name: str
    description: str
    icon: str


# ========== COMMAND =========


@dataclass(frozen=True)
class AddWorkingHoursCommand:
    advisor_id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    timezone: str = 'UTC'


@dataclass(frozen=True)
class UpdateWorkingHoursCommand:
    working_hours_id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    timezone: str


@dataclass(frozen=True)
class DeleteWorkingHoursCommand:
    working_hours_id: UUID


@dataclass(frozen=True)
class AddDayOffCommand:
    advisor_id: UUID
    date: date
    reason: str | None = None


@dataclass(frozen=True)
class DeleteDayOffCommand:
    day_off_id: UUID
