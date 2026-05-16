"""API routes for user management."""

import uuid
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.repositories.idempotency_repository import IdempotencyRepository
from src.domain.repositories.settings_repository import UserSettingsRepository
from src.domain.services.safety_rule_guard import SafetyRuleGuard
from src.presentation.api.auth import (
    Scope,
    User,
    UserManager,
    current_active_user,
    get_async_session,
    get_user_manager,
    require_scope,
)
from src.presentation.dependencies.providers import (
    get_idempotency_repository,
    get_user_settings_repository,
    get_container,
)
from src.presentation.schemas.auth import (
    UserRead,
    UserSettingsRead,
    UserSettingsUpdate,
    UserUpdate,
)

logger = structlog.get_logger(__name__)


router = APIRouter(prefix='/users', tags=['users'])


@router.get('/me', response_model=UserRead)
async def get_me(
    user: Annotated[User, Depends(current_active_user)],
) -> User:
    """Get the current authenticated user's profile."""
    return user


@router.get('/me/settings', response_model=UserSettingsRead)
async def get_my_settings(
    user: Annotated[User, Depends(current_active_user)],
    settings_repo: Annotated[
        UserSettingsRepository, Depends(get_user_settings_repository),
    ],
) -> UserSettingsRead:
    """Get the current authenticated user's settings."""
    settings = await settings_repo.get_by_user_id(user.id)
    return UserSettingsRead(
        auto_draft_enabled=settings.auto_draft_enabled,
        ai_tone=settings.ai_tone,
        signature=settings.signature,
        safety_rules=settings.safety_rules,
    )


@router.patch('/me/settings', response_model=UserSettingsRead)
async def update_my_settings(
    update: UserSettingsUpdate,
    user: Annotated[User, Depends(current_active_user)],
    settings_repo: Annotated[
        UserSettingsRepository, Depends(get_user_settings_repository),
    ],
    safety_guard: Annotated[
        SafetyRuleGuard,
        Depends(lambda c=Depends(get_container): c.safety_rule_guard),
    ],
) -> UserSettingsRead:
    """Update the current authenticated user's settings."""
    settings = await settings_repo.get_by_user_id(user.id)

    if update.auto_draft_enabled is not None:
        settings.update_auto_draft(update.auto_draft_enabled)
    if update.ai_tone is not None:
        settings.update_ai_tone(update.ai_tone)
    if update.signature is not None:
        settings.update_signature(update.signature)
    if update.safety_rules is not None:
        # Validate rules before updating
        safety_guard.validate(update.safety_rules)
        settings.update_safety_rules(update.safety_rules)

    await settings_repo.save(settings)

    return UserSettingsRead(
        auto_draft_enabled=settings.auto_draft_enabled,
        ai_tone=settings.ai_tone,
        signature=settings.signature,
        safety_rules=settings.safety_rules,
    )


@router.patch('/{user_id}', response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    user_update: UserUpdate,
    request: Request,
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
    _admin: Annotated[User, Depends(require_scope(Scope.USERS_WRITE))],
    idempotency_repo: Annotated[
        IdempotencyRepository, Depends(get_idempotency_repository),
    ],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> User:
    """Update a user's information, including their role (Admin only)."""
    user = await user_manager.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if idempotency_key:
        idemp_key = UUID(idempotency_key)
        if await idempotency_repo.check_key(idemp_key):
            logger.info('Idempotency hit for update_user', idempotency_key=str(idemp_key))
            return user

    updated_user = await user_manager.update(user_update, user, request=request)

    if idempotency_key:
        await idempotency_repo.record_key(UUID(idempotency_key))

    return updated_user


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
