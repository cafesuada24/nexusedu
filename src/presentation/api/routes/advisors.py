"""API routes for Advisor management and Leaderboards."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from src.domain.repositories.interfaces import AdvisorRepository
from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.dependencies.providers import get_advisor_repository
from src.core.logger import logger

router = APIRouter(prefix='/advisors', tags=['advisors'])


@router.get('/engagement')
async def get_engagement_metrics(
    advisor_repo: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
    _user: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
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
            status_code=500, detail='Failed to retrieve engagement metrics'
        ) from e


@router.get('/leaderboard')
async def get_leaderboard(
    advisor_repo: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
    _user: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
    time_window: str = Query(
        'all_time',
        pattern='^(weekly|monthly|semester|all_time)$',
    ),
) -> list[dict[str, Any]]:
    """Retrieve the advisor leaderboard based on gamification points.

    Args:
        advisor_repo: The advisor repository dependency.
        _user: Authenticated user with read access.
        time_window: The time window for the leaderboard.

    Returns:
        List of advisors and their scores.
    """
    try:
        return await advisor_repo.get_leaderboard(time_window)
    except Exception as e:
        logger.error(f'Failed to fetch leaderboard: {e}')
        raise HTTPException(
            status_code=500, detail='Failed to retrieve leaderboard'
        ) from e
