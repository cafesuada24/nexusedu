"""API routes for user management."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.auth import User, UserRole, Scope, require_scope, current_active_user, get_user_manager, UserManager
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
    """Update a user's information, including their role (Admin only)."""
    # Note: We can fetch the user first if we want to verify existence
    # but user_manager.update handles it.
    
    # We need to find the user in the DB first because fastapi-users update 
    # takes the user object, not just ID.
    user = await user_manager.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        
    return await user_manager.update(user_update, user, request=request)

@router.get('/', response_model=list[UserRead])
async def list_users(
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
    _admin: Annotated[User, Depends(require_scope(Scope.USERS_READ))],
) -> list[User]:
    """List all users (Admin only)."""
    # This is a bit of a hack for SQLAlchemyBaseUserTable
    # In a real app, you'd use a repository or direct DB query.
    # For now, we'll try to use the user_db if accessible or session.
    from src.api.auth import async_session_maker
    from sqlalchemy import select
    
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        return list(result.scalars().all())
