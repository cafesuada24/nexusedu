"""Pydantic schemas for Advisor profiles."""

import uuid
from typing import Optional

from pydantic import BaseModel


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

    class Config:
        from_attributes = True


class AdvisorProfileUpdate(BaseModel):
    """Schema for updating an advisor's profile."""

    name: str | None = None
    title: str | None = None
    phone: str | None = None
    faculty: str | None = None
    office: str | None = None
    bio: str | None = None
