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
from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.dependencies.providers import (
    get_advisor_query_handler,
)
from src.presentation.dtos.pagination import PagedResponse, PaginationMetadata

router = APIRouter(prefix='/advisors', tags=['advisors'])


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
