"""API routes for Advisor management and Leaderboards."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from src.application.dtos.advisor_dtos import (
    AdvisorProfileDTO,
    GetAdvisorProfileQuery,
    PersonalAdvisorMetricsDTO,
)
from src.application.dtos.gamification_dtos import (
    GetLeaderboardQuery,
    LeaderboardEntryDTO,
)
from src.application.dtos.pagination import PagedResponse
from src.application.queries.advisor_queries import (
    AdvisorQueryHandler,
)
from src.core.logger import logger
from src.domain.exceptions import AdvisorNotFoundError, UserIsNotAnAdvisorError
from src.domain.repositories.interfaces import AdvisorRepository
from src.domain.value_objects.gamification import RankingType
from src.presentation.api.auth import Scope, User, current_active_user, require_scope
from src.presentation.dependencies.providers import (
    get_advisor_query_handler,
    get_advisor_repository,
)
from src.presentation.schemas.advisor import AdvisorProfileUpdate

router = APIRouter(prefix='/advisors', tags=['advisors'])

@router.get('/profile')
async def get_my_profile(
    advisor_query_handler: Annotated[
        AdvisorQueryHandler,
        Depends(get_advisor_query_handler),
    ],
    user: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
) -> AdvisorProfileDTO:
    """Get the current user's advisor profile."""
    try:
        return await advisor_query_handler.handle_get_user_advisor_profile(user.id)
    except (UserIsNotAnAdvisorError, AdvisorNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch('/profile')
async def update_my_profile(
    update_data: AdvisorProfileUpdate,
    user: Annotated[User, Depends(current_active_user)],
    advisor_repo: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
) -> AdvisorProfileDTO:
    """Update the current user's advisor profile."""
    advisor_entity = await advisor_repo.get_by_user_id(user.id)

    # Apply updates
    if update_data.name is not None:
        advisor_entity.name = update_data.name
    if update_data.title is not None:
        advisor_entity.title = update_data.title
    if update_data.phone is not None:
        advisor_entity.phone = update_data.phone
    if update_data.faculty is not None:
        advisor_entity.faculty = update_data.faculty
    if update_data.office is not None:
        advisor_entity.office = update_data.office
    if update_data.bio is not None:
        advisor_entity.bio = update_data.bio

    await advisor_repo.save(advisor_entity)

    # Return refreshed DTO
    return AdvisorProfileDTO(
        advisor_id=advisor_entity.advisor_id,
        name=advisor_entity.name,
        email=advisor_entity.email,
        title=advisor_entity.title,
        phone=advisor_entity.phone,
        faculty=advisor_entity.faculty,
        office=advisor_entity.office,
        bio=advisor_entity.bio,
    )

@router.get('/profile/{advisor_id}')
async def get_advisor_profile(
    advisor_id: UUID,
    advisor_query_handler: Annotated[
        AdvisorQueryHandler,
        Depends(get_advisor_query_handler),
    ],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
    metrics: bool = False,
) -> AdvisorProfileDTO:
    """Get the current user's advisor profile."""
    try:
        query = GetAdvisorProfileQuery(advisor_id=advisor_id, include_metrics=metrics)
        return await advisor_query_handler.handle_get_advisor_profile(query)
    except AdvisorNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@router.get('/me/points')
async def get_my_points(
    user: Annotated[User, Depends(current_active_user)],
    advisor_query_handler: Annotated[
        AdvisorQueryHandler,
        Depends(get_advisor_query_handler),
    ],
) -> dict[str, int]:
    """Get the current user's advisor points."""
    try:
        points = await advisor_query_handler.handle_get_user_advisor_points(user.id)
        return {"points": points}
    except (UserIsNotAnAdvisorError, AdvisorNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get('/leaderboard')
async def get_leaderboard(
    query_handler: Annotated[AdvisorQueryHandler, Depends(get_advisor_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
    time_window: RankingType = RankingType.ALL_TIME,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> PagedResponse[LeaderboardEntryDTO]:
    """Retrieve the advisor leaderboard based on gamification points.

    Args:
        query_handler: The advisor query handler dependency.
        _: Authenticated user with read access.
        time_window: The time window for the leaderboard.
        limit: The maximum number of entries to return.
        offset: The number of entries to skip.

    Returns:
        List of advisors and their scores.
    """
    try:
        query = GetLeaderboardQuery(
            time_window=time_window,
            limit=limit,
            offset=offset,
        )
        return await query_handler.handle_get_leaderboard(query)
    except Exception as e:
        logger.error(f'Failed to fetch leaderboard: {e}')
        raise HTTPException(
            status_code=500,
            detail='Failed to retrieve leaderboard',
        ) from e


@router.get('/{advisor_id}/metrics')
async def get_advisor_metrics(
    advisor_id: UUID,
    query_handler: Annotated[AdvisorQueryHandler, Depends(get_advisor_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
) -> PersonalAdvisorMetricsDTO:
    """Retrieve personal performance metrics for a specific advisor."""
    try:
        return await query_handler.handle_get_advisor_metrics(advisor_id)
    except AdvisorNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f'Failed to fetch metrics for advisor {advisor_id}: {e}')
        raise HTTPException(
            status_code=500,
            detail='Failed to retrieve advisor metrics',
        ) from e


