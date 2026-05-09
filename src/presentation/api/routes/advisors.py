"""API routes for Advisor management and Leaderboards."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from src.application.dtos.advisor_dtos import (
    AdvisorProfileDTO,
    GetAdvisorProfileQuery,
)
from src.application.dtos.gamification_dtos import LeaderboardEntryDTO
from src.application.queries.advisor_queries import (
    AdvisorQueryHandler,
)
from src.core.logger import logger
from src.domain.exceptions import AdvisorNotFoundError, UserIsNotAnAdvisorError
from src.domain.repositories.interfaces import AdvisorRepository
from src.presentation.api.auth import Scope, User, current_active_user, require_scope
from src.presentation.dependencies.providers import (
    get_advisor_query_handler,
    get_advisor_repository,
)
from src.presentation.dtos.pagination import PagedResponse, PaginationMetadata
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
        return {'points': points}
    except (UserIsNotAnAdvisorError, AdvisorNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# @router.get('/profile/{advisor_id}/badges')
# async def get_advisor_badges(
#     advisor_id: str,
#     query_handler: Annotated[AdvisorQueryHandler, Depends(get_advisor_query_handler)],
#     _: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
# ) -> list[dict[str, Any]]:
#     """Retrieve the badges earned by an advisor (with Redis caching)."""
#     try:
#         adv_uuid = UUID(advisor_id)
#         badges = await query_handler.handle_get_advisor_badges(adv_uuid)
#
#         return [
#             {
#                 'badge_id': b.badge_id,
#                 'name': b.name,
#                 'description': b.description,
#                 'icon': b.icon,
#             }
#             for b in badges
#         ]
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail='Invalid advisor ID format') from e
#     except Exception as e:
#         logger.error(f'Failed to fetch badges for advisor {advisor_id}: {e}')
#         raise HTTPException(
#             status_code=500,
#             detail='Failed to retrieve advisor badges',
#         ) from e


# @router.get('/engagement')
# async def get_engagement_metrics(
#     query_handler: Annotated[AdvisorQueryHandler, Depends(get_advisor_query_handler)],
#     _: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
# ) -> list[dict[str, Any]]:
#     """Retrieve engagement metrics aggregated by major (faculty).
#
#     Returns:
#         List of majors and their sent/drafted counts.
#     """
#     try:
#         metrics = await query_handler.handle_get_engagement_metrics()
#         return [
#             {
#                 'major': m.major,
#                 'sent_count': m.sent_count,
#                 'drafted_count': m.drafted_count,
#             }
#             for m in metrics
#         ]
#     except Exception as e:
#         logger.error(f'Failed to fetch engagement metrics: {e}')
#         raise HTTPException(
#             status_code=500,
#             detail='Failed to retrieve engagement metrics',
#         ) from e


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
    """Retrieve the advisor leaderboard based on gamification points."""
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
