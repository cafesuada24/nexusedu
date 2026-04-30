"""Authentication and authorization management.

This module sets up FastAPI-Users with JWT authentication, SQLAlchemy database
backend, and role-based access control (RBAC).
"""

import uuid
from collections.abc import AsyncGenerator, Callable
from enum import Enum, StrEnum
from typing import Annotated, override

from fastapi import Depends, HTTPException, Request, status
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import Base, User
from src.infrastructure.database.session import engine, get_async_session
from src.utils.env import getenv

# Configuration
JWT_SECRET: str = getenv(
    'JWT_SECRET',
    'SET_ME_IN_PRODUCTION_HEHEHE',
)


class Scope(StrEnum):
    """Granular permissions (capabilities) in the system."""

    ALERTS_READ = 'alerts:read'
    ALERTS_WRITE = 'alerts:write'
    ADVISORS_READ = 'advisors:read'
    DATA_INGEST = 'data:ingest'
    JOBS_READ = 'jobs:read'
    QUERY_EXECUTE = 'query:execute'
    USERS_READ = 'users:read'
    USERS_WRITE = 'users:write'


class UserRole(StrEnum):
    """Simplified user roles."""

    ADMIN = 'admin'
    ADVISOR = 'advisor'
    VIEWER = 'viewer'


# Map roles to their specific capabilities
ROLE_PERMISSIONS: dict[UserRole, set[Scope]] = {
    UserRole.ADMIN: set(Scope),  # Full access
    UserRole.ADVISOR: {
        Scope.ALERTS_READ,
        Scope.ALERTS_WRITE,
        Scope.ADVISORS_READ,
        Scope.JOBS_READ,
        Scope.QUERY_EXECUTE,
    },
    UserRole.VIEWER: {
        Scope.ALERTS_READ,
        Scope.ADVISORS_READ,
        Scope.JOBS_READ,
    },
}


async def create_db_and_tables() -> None:
    """Creates the database and all tables defined in Base."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_user_db(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AsyncGenerator[SQLAlchemyUserDatabase[User, uuid.UUID], None]:
    """Dependency for getting the user database adapter."""
    yield SQLAlchemyUserDatabase(session, User)


# User Manager
class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """User manager for handling user registration, login, and security tokens."""

    reset_password_token_secret = JWT_SECRET
    verification_token_secret = JWT_SECRET

    @override
    async def on_after_register(
        self,
        user: User,
        _request: Request | None = None,
    ) -> None:
        """Callback triggered after a user successfully registers."""
        print(f'User {user.id} has registered.')


async def get_user_manager(
    user_db: Annotated[SQLAlchemyUserDatabase[User, uuid.UUID], Depends(get_user_db)],
) -> AsyncGenerator[UserManager, None]:
    """Dependency for getting the user manager instance."""
    yield UserManager(user_db)


# Authentication Backend
bearer_transport = BearerTransport(tokenUrl='api/v1/auth/jwt/login')


def get_jwt_strategy() -> JWTStrategy:
    """Strategy for generating and validating JWT tokens."""
    return JWTStrategy(secret=JWT_SECRET, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name='jwt',
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# FastAPI Users Instance
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

current_active_user: Callable[..., User] = fastapi_users.current_user(active=True)


# RBAC Utilities
def require_scope(required_scope: Scope) -> Callable[[User], User]:
    """Dependency for checking if a user has the required capability."""

    def scope_checker(
        user: Annotated[User, Depends(current_active_user)],
    ) -> User:
        """Inner dependency that performs the scope check."""
        try:
            user_role = UserRole(user.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'Forbidden: Invalid role "{user.role}"',
            ) from None

        # Check if the user's role has the required scope
        user_scopes = ROLE_PERMISSIONS.get(user_role, set())
        if required_scope in user_scopes:
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f'Forbidden: Insufficient permissions (requires {required_scope.value})',
        )

    return scope_checker


def check_role(role_string: str) -> Callable[[User], User]:
    """Dependency for checking if a user has permissions associated with a role name."""
    if role_string == UserRole.ADMIN.value:
        return require_scope(Scope.USERS_WRITE)
    if role_string == UserRole.ADVISOR.value:
        return require_scope(Scope.ALERTS_WRITE)

    return require_scope(Scope.ALERTS_READ)
