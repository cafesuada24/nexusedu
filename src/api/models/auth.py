"""Pydantic models for authentication and user management."""

import uuid

from fastapi_users import schemas

from src.api.auth import UserRole


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema for reading user data."""

    role: UserRole


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a new user.
    
    Role is intentionally excluded to prevent self-assignment during registration.
    It defaults to 'advisor:read' in the database model.
    """

    pass


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating an existing user."""

    role: UserRole | None = None
