"""API routes for Advisor management and Leaderboards."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from src.application.dtos.advisor_dtos import LeaderboardEntryDTO
from src.application.queries.advisor_queries import (
    AdvisorQueryHandler,
    GetLeaderboardQuery,
)
from src.core.logger import logger
from src.domain.repositories.badge_repository import BadgeRepository
from src.domain.repositories.interfaces import AdvisorRepository
from src.domain.value_objects.badges import BADGE_MAP
from src.presentation.api.auth import Scope, User, current_active_user, require_scope
from src.presentation.dependencies.providers import (
    get_advisor_query_handler,
)
from src.presentation.dtos.pagination import PagedResponse, PaginationMetadata

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
        raise HTTPException(status_code=404, detail='Advisor profile not found')
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
    from src.presentation.schemas.advisor import AdvisorProfileRead, AdvisorProfileUpdate

    # Validate payload
    try:
        validated_data = AdvisorProfileUpdate(**update_data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    advisor = await advisor_repo.get_by_user_id(user.id)
    if not advisor:
        raise HTTPException(status_code=404, detail='Advisor profile not found')

    update_dict = {k: v for k, v in validated_data.model_dump().items() if v is not None}
    if not update_dict:
        return AdvisorProfileRead.model_validate(advisor)

    updated_advisor = await advisor_repo.update_profile(advisor.advisor_id, update_dict)
    return AdvisorProfileRead.model_validate(updated_advisor)


@router.get('/engagement')
async def get_engagement_metrics(
    query_handler: Annotated[AdvisorQueryHandler, Depends(get_advisor_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
) -> list[dict[str, Any]]:
    """Retrieve engagement metrics aggregated by major (faculty).

    Returns:
        List of majors and their sent/drafted counts.
    """
    try:
        metrics = await query_handler.handle_get_engagement_metrics()
        return [
            {
                'major': m.major,
                'sent_count': m.sent_count,
                'drafted_count': m.drafted_count,
            }
            for m in metrics
        ]
    except Exception as e:
        logger.error(f'Failed to fetch engagement metrics: {e}')
        raise HTTPException(
            status_code=500,
            detail='Failed to retrieve engagement metrics',
        ) from e


@router.get('/leaderboard')
async def get_leaderboard(
    query_handler: Annotated[AdvisorQueryHandler, Depends(get_advisor_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
    time_window: str = Query(
        'all_time',
        pattern='^(weekly|monthly|semester|all_time)$',
    ),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> PagedResponse[LeaderboardEntryDTO]:
    """Retrieve the advisor leaderboard based on gamification points.

    Args:
        query_handler: The advisor query handler dependency.
        _user: Authenticated user with read access.
        time_window: The time window for the leaderboard.

    Returns:
        List of advisors and their scores.
    """
    try:
        query = GetLeaderboardQuery(
            time_window=time_window,
            limit=limit,
            offset=offset,
        )
        entries, total_count = await query_handler.handle_get_leaderboard(query)
        return PagedResponse(
            items=entries,
            metadata=PaginationMetadata(
                total_count=total_count,
                limit=limit,
                offset=offset,
                has_next=(query.offset + query.limit) < total_count,
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
    query_handler: Annotated[AdvisorQueryHandler, Depends(get_advisor_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
) -> list[dict[str, Any]]:
    """Retrieve the badges earned by an advisor (with Redis caching)."""
    try:
        adv_uuid = UUID(advisor_id)
        badges = await query_handler.handle_get_advisor_badges(adv_uuid)

        return [
            {
                'badge_id': b.badge_id,
                'name': b.name,
                'description': b.description,
                'icon': b.icon,
            }
            for b in badges
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail='Invalid advisor ID format') from e
    except Exception as e:
        logger.error(f'Failed to fetch badges for advisor {advisor_id}: {e}')
        raise HTTPException(
            status_code=500,
            detail='Failed to retrieve advisor badges',
        ) from e
