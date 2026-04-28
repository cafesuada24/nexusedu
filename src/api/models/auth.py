"""Pydantic models for authentication and user management."""

import uuid

from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema for reading user data."""

    role: str


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a new user."""

    role: str | None = 'advisor:read'


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating an existing user."""

    role: str | None = None
