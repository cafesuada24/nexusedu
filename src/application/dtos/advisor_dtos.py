"""DTOs for advisor-related operations."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, NonNegativeInt, PositiveInt
from pydantic_extra_types.phone_numbers import PhoneNumber, PhoneNumberValidator

# ========== QUERY =========

@dataclass(frozen=True)
class GetUsersAdvisorProfileQuery:
    user_id: UUID


@dataclass(frozen=True)
class GetAdvisorProfileQuery:
    advisor_id: UUID
    include_metrics: bool

class AdvisorMetricsDTO(BaseModel):
    points: PositiveInt = 0


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

    metrics: AdvisorMetricsDTO | None = None


@dataclass(frozen=True)
class BadgeDTO:
    """DTO for an achievement badge."""

    badge_id: str
    name: str
    description: str
    icon: str
