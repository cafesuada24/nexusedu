"""Authentication and authorization management.

This module sets up FastAPI-Users with JWT authentication, SQLAlchemy database
backend, and role-based access control (RBAC).
"""

import os
import uuid
from collections.abc import AsyncGenerator, Callable
from typing import Annotated, override

from fastapi import Depends, HTTPException, Request, status
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'SECRET_CHANGE_ME_IN_PRODUCTION')
DATABASE_URL = 'sqlite+aiosqlite:///./auth.db'

# Database Setup
class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    """SQLAlchemy model for the User table."""

    role: Mapped[str] = mapped_column(default='advisor:read')


engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables() -> None:
    """Creates the database and all tables defined in Base."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting an asynchronous SQLAlchemy session."""
    async with async_session_maker() as session:
        yield session


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
bearer_transport = BearerTransport(tokenUrl='auth/jwt/login')


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

current_active_user = fastapi_users.current_user(active=True)


# RBAC Utilities
def check_role(required_role: str) -> Callable[[User], User]:
    """Dependency for checking if a user has the required role.

    Args:
        required_role: The role name required to access the endpoint.

    Returns:
        A dependency function that validates the user's role.
    """

    def role_checker(
        user: Annotated[User, Depends(current_active_user)],
    ) -> User:
        """Inner dependency that performs the role check."""
        # admin:all has full access
        if user.role == 'admin:all':
            return user

        # Exact match
        if user.role == required_role:
            return user

        # Hierarchy: advisor:write can do advisor:read
        if required_role == 'advisor:read' and user.role == 'advisor:write':
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Forbidden: Insufficient role',
        )

    return role_checker
