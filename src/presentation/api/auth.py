"""Authentication and authorization management.

This module sets up FastAPI-Users with JWT authentication, SQLAlchemy database
backend, and role-based access control (RBAC).
"""

import uuid
from collections.abc import AsyncGenerator, Callable
from enum import StrEnum
from typing import Annotated, Any, override

from fastapi import Depends, HTTPException, Request, status
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_db_sqlalchemy import BaseUserDatabase, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import config
from src.core.logger import logger
from src.domain.repositories.advisor_repository import AdvisorRepository
from src.domain.repositories.settings_repository import UserSettingsRepository
from src.infrastructure.database.models import User
from src.infrastructure.database.session import get_async_session
from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
    SqlAlchemyAdvisorRepository,
    SqlAlchemyUserSettingsRepository,
)
from src.presentation.dependencies.providers import (
    get_advisor_repository,
    get_user_settings_repository,
)

# Configuration
if config.jwt_secret is None:
    if config.environment == 'production':
        raise ValueError(
            'config.jwt_secret variable is required in production environment.',
        )
    config.jwt_secret = 'SET_ME_IN_PRODUCTION_HAHAH'


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

    CASE_ACCEPT = 'case:accept'
    CASE_READ = 'case:read'


class UserRole(StrEnum):
    """Simplified user roles."""

    ADMIN = 'admin'
    ADVISOR = 'advisor'
    VIEWER = 'viewer'


# Map roles to their specific capabilities
ROLE_PERMISSIONS: dict[UserRole, set[Scope]] = {
    UserRole.ADMIN: set(Scope) - set({Scope.CASE_ACCEPT}),  # Full access
    UserRole.ADVISOR: {
        Scope.ALERTS_READ,
        Scope.ALERTS_WRITE,
        Scope.ADVISORS_READ,
        Scope.JOBS_READ,
        Scope.QUERY_EXECUTE,
        Scope.CASE_ACCEPT,
        Scope.CASE_READ,
    },
    UserRole.VIEWER: {
        Scope.ALERTS_READ,
        Scope.ADVISORS_READ,
    },
}


async def get_user_db(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AsyncGenerator[BaseUserDatabase[User, uuid.UUID], None]:
    """Dependency for getting the user database adapter."""
    yield SQLAlchemyUserDatabase(session, User)


# User Manager
class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """User manager for handling user registration, login, and security tokens."""

    reset_password_token_secret = config.jwt_secret
    verification_token_secret = config.jwt_secret

    def __init__(
        self,
        user_db: BaseUserDatabase[User, uuid.UUID],
        user_settings_db: UserSettingsRepository,
        advisor_repo: AdvisorRepository,
    ):
        super().__init__(user_db)
        self._user_setting_db = user_settings_db
        self._advisor_repo = advisor_repo

    @override
    async def on_after_register(
        self,
        user: User,
        _request: Request | None = None,
    ) -> None:
        """Callback triggered after a user successfully registers."""
        logger.info(f'User {user.id} has registered.')
        await self._user_setting_db.create_user_settings(user.id)

        if user.role == UserRole.ADVISOR.value:
            # Ensure an advisor profile exists and is linked
            name = user.email.split('@')[0].capitalize()
            await self._advisor_repo.upsert_advisor_for_user(user.id, user.email, name)

    @override
    async def on_after_update(
        self,
        user: User,
        _update_dict: dict[str, Any],
        _request: Request | None = None,
    ) -> None:
        """Callback triggered after a user is updated."""
        if user.role == UserRole.ADVISOR.value:
            # Ensure an advisor profile exists and is linked
            name = user.email.split('@')[0].capitalize()
            await self._advisor_repo.upsert_advisor_for_user(user.id, user.email, name)


async def get_user_manager(
    user_db: Annotated[SQLAlchemyUserDatabase[User, uuid.UUID], Depends(get_user_db)],
    user_settings_db: Annotated[
        SqlAlchemyUserSettingsRepository,
        Depends(get_user_settings_repository),
    ],
    advisor_repo: Annotated[
        SqlAlchemyAdvisorRepository,
        Depends(get_advisor_repository),
    ],
) -> AsyncGenerator[UserManager, None]:
    """Dependency for getting the user manager instance."""
    yield UserManager(user_db, user_settings_db, advisor_repo)


# Authentication Backend
bearer_transport = BearerTransport(tokenUrl='api/v1/auth/jwt/login')


def get_jwt_strategy() -> JWTStrategy:
    """Strategy for generating and validating JWT tokens."""
    # matches frontend cookie maxAge in app/actions/auth.ts
    return JWTStrategy(secret=config.jwt_secret, lifetime_seconds=28800)


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
