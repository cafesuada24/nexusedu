"""Pydantic models for authentication and user management."""

import uuid

from typing import Literal

from fastapi_users import schemas
from pydantic import Field

from src.presentation.api.auth import UserRole


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema for reading user data."""

    role: UserRole


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a new user.

    Role is intentionally excluded to prevent self-assignment during registration.
    It defaults to 'viewer' in the database model.
    """

    pass


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating an existing user.

    Attributes:
        role: The new role to assign to the user.
    """

    role: UserRole | None = None


class UserSettingsRead(schemas.BaseModel):
    """Schema for reading user settings."""

    auto_draft_enabled: bool
    ai_tone: str
    signature: str | None
    safety_rules: list[str]


class UserSettingsUpdate(schemas.BaseModel):
    """Schema for updating user settings."""

    auto_draft_enabled: bool | None = None
    ai_tone: Literal['warm', 'formal', 'direct', 'motivational'] | None = None
    signature: str | None = None
    safety_rules: list[str] | None = None
