"""Pydantic models for authentication and user management."""

import uuid

from fastapi_users import schemas

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


class UserSettingsUpdate(schemas.BaseModel):
    """Schema for updating user settings."""

    auto_draft_enabled: bool | None = None
