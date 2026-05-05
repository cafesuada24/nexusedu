"""Pydantic schemas for Advisor profiles."""

import uuid
from typing import Optional

from pydantic import BaseModel


class AdvisorProfileRead(BaseModel):
    """Schema for reading an advisor's profile."""

    advisor_id: uuid.UUID
    name: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    faculty: Optional[str] = None
    office: Optional[str] = None
    bio: Optional[str] = None

    class Config:
        from_attributes = True


class AdvisorProfileUpdate(BaseModel):
    """Schema for updating an advisor's profile."""

    name: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    faculty: Optional[str] = None
    office: Optional[str] = None
    bio: Optional[str] = None
