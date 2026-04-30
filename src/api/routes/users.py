"""API routes for user management."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import (
    Scope,
    User,
    UserManager,
    current_active_user,
    get_async_session,
    get_user_manager,
    require_scope,
)
from src.api.models.auth import UserRead, UserUpdate

router = APIRouter(prefix='/users', tags=['users'])


@router.get('/me', response_model=UserRead)
async def get_me(
    user: Annotated[User, Depends(current_active_user)],
) -> User:
    """Get the current authenticated user's profile."""
    return user


@router.patch('/{user_id}', response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    user_update: UserUpdate,
    request: Request,
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
    _admin: Annotated[User, Depends(require_scope(Scope.USERS_WRITE))],
) -> User:
    """Update a user's information, including their role (Admin only).

    Args:
        user_id: The ID of the user to update.
        user_update: The update data.
        request: The incoming request object.
        user_manager: The user manager dependency.
        _admin: Dependency to ensure the requester has admin permissions.

    Returns:
        The updated user object.

    Raises:
        HTTPException: If the user is not found.
    """
    user = await user_manager.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return await user_manager.update(user_update, user, request=request)


@router.get('/', response_model=list[UserRead])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    _admin: Annotated[User, Depends(require_scope(Scope.USERS_READ))],
) -> list[User]:
    """List all users (Admin only).

    Args:
        session: The database session dependency.
        _admin: Dependency to ensure the requester has read permissions for users.

    Returns:
        A list of all users.
    """
    result = await session.execute(select(User))
    return list(result.scalars().all())
