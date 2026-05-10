"""Pydantic schemas for Advisor profiles."""

import uuid
from datetime import date, time

from pydantic import BaseModel, ConfigDict


class AdvisorProfileRead(BaseModel):
    """Schema for reading an advisor's profile."""

    advisor_id: uuid.UUID
    name: str | None = None
    email: str | None = None
    title: str | None = None
    phone: str | None = None
    faculty: str | None = None
    office: str | None = None
    bio: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AdvisorProfileUpdate(BaseModel):
    """Schema for updating an advisor's profile."""

    name: str | None = None
    title: str | None = None
    phone: str | None = None
    faculty: str | None = None
    office: str | None = None
    bio: str | None = None


class WorkingHoursRead(BaseModel):
    id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    timezone: str

    model_config = ConfigDict(from_attributes=True)


class DayOffRead(BaseModel):
    id: uuid.UUID
    date: date
    reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AdvisorScheduleRead(BaseModel):
    working_hours: list[WorkingHoursRead]
    days_off: list[DayOffRead]


class WorkingHoursCreate(BaseModel):
    day_of_week: int
    start_time: time
    end_time: time
    timezone: str = 'UTC'


class WorkingHoursUpdate(BaseModel):
    day_of_week: int
    start_time: time
    end_time: time
    timezone: str


class DayOffCreate(BaseModel):
    date: date
    reason: str | None = None
