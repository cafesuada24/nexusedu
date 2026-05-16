"""Authentication and authorization management.

This module sets up FastAPI-Users with JWT authentication, SQLAlchemy database
backend, and role-based access control (RBAC).
"""

import uuid
from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, override

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users.jwt import generate_jwt
from fastapi_users_db_sqlalchemy import BaseUserDatabase, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.worker_payloads.case_payloads import AdvisorCreatedPayload
from src.application.interfaces.unit_of_work import UnitOfWork
from src.core.config import config
from src.domain.repositories.settings_repository import UserSettingsRepository
from src.infrastructure.database.models import User
from src.infrastructure.database.session import get_async_session
from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
    SqlAlchemyUserSettingsRepository,
)
from src.presentation.dependencies.providers import (
    get_unit_of_work,
    get_user_settings_repository,
)

logger = structlog.get_logger(__name__)


class Scope(StrEnum):
    """Granular permissions (capabilities) in the system."""

    ALERTS_READ = 'alerts:read'
    ALERTS_WRITE = 'alerts:write'
    ADVISORS_READ = 'advisors:read'
    ADVISORS_WRITE = 'advisors:write'

    ADMIN_DASHBOARD = 'admin:dashboard'

    DATA_INGEST = 'data:ingest'
    JOBS_READ = 'jobs:read'
    QUERY_EXECUTE = 'query:execute'
    USERS_READ = 'users:read'
    USERS_WRITE = 'users:write'

    CASE_ACCEPT = 'case:accept'
    CASE_READ = 'case:read'
    CASE_READ_ALL = 'case:read_all'

    STUDENTS_READ = 'students:read'
    STUDENTS_WRITE = 'students:write'


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
        Scope.ADVISORS_WRITE,
        Scope.JOBS_READ,
        Scope.QUERY_EXECUTE,
        Scope.CASE_ACCEPT,
        Scope.CASE_READ,
        Scope.STUDENTS_READ,
    },
    UserRole.VIEWER: {
        Scope.ALERTS_READ,
        Scope.ADVISORS_READ,
        Scope.STUDENTS_READ,
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
        uow: UnitOfWork,
    ) -> None:
        """Initialize the user manager with required repositories."""
        super().__init__(user_db)
        self._user_setting_db = user_settings_db
        self._uow = uow

    @override
    async def on_after_register(
        self,
        user: User,
        _: Request | None = None,
    ) -> None:
        """Callback triggered after a user successfully registers."""
        logger.info('User registered', user_id=user.id)

        # Derive name from email if not provided (placeholder for registration form name)
        name = user.email.split('@')[0].replace('.', ' ').replace('_', ' ').capitalize()
        await self._user_setting_db.create_user_settings(user.id, name=name)

        if user.role == UserRole.ADVISOR.value:
            # Ensure an advisor profile exists and is linked
            async with self._uow:
                advisor_id, created = await self._uow.advisors.upsert_advisor_for_user(
                    user.id,
                    user.email,
                    name,
                )
                if created:
                    await self._uow.enqueue(
                        'run_advisor_created_task',
                        payload=AdvisorCreatedPayload(
                            advisor_id=advisor_id,
                            email=user.email,
                            name=name,
                            occurred_at=datetime.now(UTC),
                        ),
                    )
                await self._uow.commit()

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
            name = (
                user.email.split('@')[0]
                .replace('.', ' ')
                .replace('_', ' ')
                .capitalize()
            )

            # Ensure settings exist (idempotent)
            await self._user_setting_db.create_user_settings(user.id, name=name)

            async with self._uow:
                advisor_id, created = await self._uow.advisors.upsert_advisor_for_user(
                    user.id,
                    user.email,
                    name,
                )
                if created:
                    await self._uow.enqueue(
                        'run_advisor_created_task',
                        payload=AdvisorCreatedPayload(
                            advisor_id=advisor_id,
                            email=user.email,
                            name=name,
                            occurred_at=datetime.now(UTC),
                        ),
                    )
                await self._uow.commit()


async def get_user_manager(
    user_db: Annotated[SQLAlchemyUserDatabase[User, uuid.UUID], Depends(get_user_db)],
    user_settings_db: Annotated[
        SqlAlchemyUserSettingsRepository,
        Depends(get_user_settings_repository),
    ],
    uow: Annotated[
        UnitOfWork,
        Depends(get_unit_of_work),
    ],
) -> AsyncGenerator[UserManager, None]:
    """Dependency for getting the user manager instance."""
    yield UserManager(user_db, user_settings_db, uow)


# Authentication Backend
cookie_transport = CookieTransport(
    cookie_name='nexusedu_auth_token',
    cookie_max_age=28800,
    cookie_httponly=True,
    cookie_samesite='lax',
    cookie_secure=config.environment == 'production',
)


class RoleJWTStrategy(JWTStrategy[User, uuid.UUID]):
    """JWT strategy that includes the user's role in the token payload."""

    async def write_token(self, user: User) -> str:
        """Create a JWT token with custom claims (role)."""
        data = {
            'sub': str(user.id),
            'aud': self.token_audience,
            'role': user.role,
        }
        return generate_jwt(
            data,
            self.decode_key,
            self.lifetime_seconds,
            algorithm=self.algorithm,
        )


def get_jwt_strategy() -> JWTStrategy[User, uuid.UUID]:
    """Strategy for generating and validating JWT tokens."""
    return RoleJWTStrategy(secret=config.jwt_secret, lifetime_seconds=28800)


auth_backend = AuthenticationBackend(
    name='jwt',
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

# FastAPI Users Instance
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

current_active_user = fastapi_users.current_user(active=True)


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
