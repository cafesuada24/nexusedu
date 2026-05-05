"""API routes for Advisor management and Leaderboards."""

import json
from typing import Annotated, Any
from uuid import UUID

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.logger import logger
from src.domain.repositories.badge_repository import BadgeRepository
from src.domain.repositories.interfaces import AdvisorRepository
from src.domain.value_objects.badges import BADGE_MAP
from src.presentation.api.auth import Scope, User, current_active_user, require_scope
from src.presentation.dependencies.providers import (
    get_advisor_repository,
    get_arq_pool,
    get_badge_repository,
)
from src.presentation.dtos.pagination import PagedResponse, PaginationMetadata
from src.presentation.schemas.response import (
    LeaderboardEntry,
)

router = APIRouter(prefix='/advisors', tags=['advisors'])


@router.get('/me/profile')
async def get_my_profile(
    user: Annotated[User, Depends(current_active_user)],
    advisor_repo: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
) -> Any:
    """Get the current user's advisor profile."""
    from src.presentation.schemas.advisor import AdvisorProfileRead
    advisor = await advisor_repo.get_by_user_id(user.id)
    if not advisor:
        raise HTTPException(status_code=404, detail="Advisor profile not found")
    return AdvisorProfileRead.model_validate(advisor)


@router.get('/me/points')
async def get_my_points(
    user: Annotated[User, Depends(current_active_user)],
    advisor_repo: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
) -> dict[str, int]:
    """Get the current user's advisor points."""
    advisor = await advisor_repo.get_by_user_id(user.id)
    if not advisor:
        raise HTTPException(status_code=404, detail="Advisor profile not found")
    
    points = await advisor_repo.get_advisor_points(advisor.advisor_id)
    return {"points": points}


@router.patch('/me/profile')
async def update_my_profile(
    update_data: dict[str, Any],
    user: Annotated[User, Depends(current_active_user)],
    advisor_repo: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
) -> Any:
    """Update the current user's advisor profile."""
    from src.presentation.schemas.advisor import AdvisorProfileUpdate, AdvisorProfileRead
    # Validate payload
    try:
        validated_data = AdvisorProfileUpdate(**update_data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    advisor = await advisor_repo.get_by_user_id(user.id)
    if not advisor:
        raise HTTPException(status_code=404, detail="Advisor profile not found")

    update_dict = {k: v for k, v in validated_data.model_dump().items() if v is not None}
    if not update_dict:
        return AdvisorProfileRead.model_validate(advisor)

    updated_advisor = await advisor_repo.update_profile(advisor.advisor_id, update_dict)
    return AdvisorProfileRead.model_validate(updated_advisor)

@router.get('/engagement')
async def get_engagement_metrics(
    advisor_repo: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
) -> list[dict[str, Any]]:
    """Retrieve engagement metrics aggregated by major (faculty).

    Returns:
        List of majors and their sent/drafted counts.
    """
    try:
        return await advisor_repo.get_engagement_metrics()
    except Exception as e:
        logger.error(f'Failed to fetch engagement metrics: {e}')
        raise HTTPException(
            status_code=500,
            detail='Failed to retrieve engagement metrics',
        ) from e


@router.get('/leaderboard')
async def get_leaderboard(
    advisor_repo: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
    time_window: str = Query(
        'all_time',
        pattern='^(weekly|monthly|semester|all_time)$',
    ),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> PagedResponse[LeaderboardEntry]:
    """Retrieve the advisor leaderboard based on gamification points.

    Args:
        advisor_repo: The advisor repository dependency.
        _user: Authenticated user with read access.
        time_window: The time window for the leaderboard.

    Returns:
        List of advisors and their scores.
    """
    try:
        items, total_count = await advisor_repo.get_leaderboard(
            time_window,
            limit=limit,
            offset=offset,
        )
        return PagedResponse(
            items=[
                LeaderboardEntry(
                    advisor_id=str(i['advisor_id']),
                    name=i['name'],
                    total_points=i['total_points'],
                    actions_count=i['actions_count'],
                    sent_count=i['sent_count'],
                    resolved_count=i['resolved_count'],
                )
                for i in items
            ],
            metadata=PaginationMetadata(
                total_count=total_count,
                limit=limit,
                offset=offset,
                has_next=(offset + limit) < total_count,
            ),
        )
    except Exception as e:
        logger.error(f'Failed to fetch leaderboard: {e}')
        raise HTTPException(
            status_code=500,
            detail='Failed to retrieve leaderboard',
        ) from e


@router.get('/{advisor_id}/badges')
async def get_advisor_badges(
    advisor_id: str,
    badge_repo: Annotated[BadgeRepository, Depends(get_badge_repository)],
    arq_pool: Annotated[ArqRedis, Depends(get_arq_pool)],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
) -> list[dict[str, Any]]:
    """Retrieve the badges earned by an advisor (with Redis caching)."""
    cache_key = f'advisor_badges:{advisor_id}'
    try:
        # 1. Try to get from cache
        cached_data = await arq_pool.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # 2. If not in cache, fetch from DB
        adv_uuid = UUID(advisor_id)
        badge_ids = await badge_repo.get_advisor_badges(adv_uuid)

        badges: list[dict[str, Any]] = []
        for b_id in badge_ids:
            if b_id in BADGE_MAP:
                b = BADGE_MAP[b_id]
                badges.append(
                    {
                        'badge_id': b.badge_id,
                        'name': b.name,
                        'description': b.description,
                        'icon': b.icon,
                    },
                )

        # 3. Store in cache for 5 minutes (300s)
        await arq_pool.setex(cache_key, 300, json.dumps(badges))

        return badges
    except ValueError as e:
        raise HTTPException(status_code=400, detail='Invalid advisor ID format') from e
    except Exception as e:
        logger.error(f'Failed to fetch badges for advisor {advisor_id}: {e}')
        raise HTTPException(
            status_code=500, detail='Failed to retrieve advisor badges',
        ) from e
