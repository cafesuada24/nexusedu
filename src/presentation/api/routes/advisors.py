"""API routes for Advisor management and Leaderboards."""

from datetime import date
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query

from src.application.commands.schedule_commands import ScheduleCommandHandler
from src.application.dtos.advisor_dtos import (
    AddDayOffCommand,
    AddWorkingHoursCommand,
    AdvisorProfileDTO,
    AdvisorScheduleDTO,
    AvailabilitySlotDTO,
    DeleteDayOffCommand,
    DeleteWorkingHoursCommand,
    GetAdvisorAvailabilityQuery,
    GetAdvisorProfileQuery,
    GetAdvisorScheduleQuery,
    GetUserAdvisorScheduleQuery,
    UpdateWorkingHoursCommand,
)
from src.application.dtos.gamification_dtos import (
    GetLeaderboardQuery,
    LeaderboardEntryDTO,
)
from src.application.dtos.pagination import PagedResponse
from src.application.queries.advisor_queries import (
    AdvisorQueryHandler,
)
from src.domain.repositories.interfaces import AdvisorRepository
from src.domain.value_objects.gamification import RankingType
from src.presentation.api.auth import Scope, User, current_active_user, require_scope
from src.presentation.dependencies.providers import (
    get_advisor_query_handler,
    get_advisor_repository,
    get_schedule_command_handler,
)
from src.presentation.schemas.advisor import (
    AdvisorProfileUpdate,
    AdvisorScheduleRead,
    DayOffCreate,
    WorkingHoursCreate,
    WorkingHoursUpdate,
)

logger = structlog.get_logger(__name__)

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
    return await advisor_query_handler.handle_get_user_advisor_profile(user.id)


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
    query = GetAdvisorProfileQuery(advisor_id=advisor_id, include_metrics=metrics)
    return await advisor_query_handler.handle_get_advisor_profile(query)


@router.get('/{advisor_id}/availability')
async def get_advisor_availability(
    advisor_id: UUID,
    advisor_query_handler: Annotated[
        AdvisorQueryHandler,
        Depends(get_advisor_query_handler),
    ],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
    start_date: Annotated[
        date,
        Query(..., description='Start date for availability check (YYYY-MM-DD)'),
    ],
    end_date: Annotated[
        date,
        Query(..., description='End date for availability check (YYYY-MM-DD)'),
    ],
) -> list[AvailabilitySlotDTO]:
    """Retrieve available appointment slots for a specific advisor."""
    query = GetAdvisorAvailabilityQuery(
        advisor_id=advisor_id,
        start_date=start_date,
        end_date=end_date,
    )
    return await advisor_query_handler.handle_get_advisor_availability(query)


@router.get('/me/points')
async def get_my_points(
    user: Annotated[User, Depends(current_active_user)],
    advisor_query_handler: Annotated[
        AdvisorQueryHandler,
        Depends(get_advisor_query_handler),
    ],
) -> dict[str, int]:
    """Get the current user's advisor points."""
    points = await advisor_query_handler.handle_get_user_advisor_points(user.id)
    return {'points': points}


# Self-service aliases
@router.get('/me/schedule', response_model=AdvisorScheduleRead)
async def get_my_schedule(
    query_handler: Annotated[AdvisorQueryHandler, Depends(get_advisor_query_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
) -> AdvisorScheduleDTO:
    """Get the current advisor's schedule."""
    query = GetUserAdvisorScheduleQuery(user_id=user.id)
    return await query_handler.handle_get_user_advisor_schedule(query)


@router.get('/{advisor_id}/schedule', response_model=AdvisorScheduleRead)
async def get_advisor_schedule(
    advisor_id: UUID,
    query_handler: Annotated[AdvisorQueryHandler, Depends(get_advisor_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
) -> AdvisorScheduleDTO:
    """Retrieve the full schedule (working hours and days off) for an advisor."""
    query = GetAdvisorScheduleQuery(advisor_id=advisor_id)
    return await query_handler.handle_get_advisor_schedule(query)


@router.post('/{advisor_id}/working-hours')
async def add_working_hours(
    advisor_id: UUID,
    request: WorkingHoursCreate,
    command_handler: Annotated[
        ScheduleCommandHandler,
        Depends(get_schedule_command_handler),
    ],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_WRITE))],
) -> dict[str, str]:
    """Add a recurring working hour block."""
    command = AddWorkingHoursCommand(
        advisor_id=advisor_id,
        day_of_week=request.day_of_week,
        start_time=request.start_time,
        end_time=request.end_time,
        timezone=request.timezone,
    )
    await command_handler.handle_add_working_hours(command)
    return {'status': 'success', 'message': 'Working hours added'}


@router.put('/working-hours/{wh_id}')
async def update_working_hours(
    wh_id: UUID,
    request: WorkingHoursUpdate,
    command_handler: Annotated[
        ScheduleCommandHandler, Depends(get_schedule_command_handler),
    ],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_WRITE))],
) -> dict[str, str]:
    """Update an existing working hour block."""
    command = UpdateWorkingHoursCommand(
        working_hours_id=wh_id,
        day_of_week=request.day_of_week,
        start_time=request.start_time,
        end_time=request.end_time,
        timezone=request.timezone,
    )
    await command_handler.handle_update_working_hours(command)
    return {'status': 'success', 'message': 'Working hours updated'}


@router.delete('/working-hours/{wh_id}')
async def delete_working_hours(
    wh_id: UUID,
    command_handler: Annotated[
        ScheduleCommandHandler, Depends(get_schedule_command_handler),
    ],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_WRITE))],
) -> dict[str, str]:
    """Delete a working hour block."""
    command = DeleteWorkingHoursCommand(working_hours_id=wh_id)
    await command_handler.handle_delete_working_hours(command)
    return {'status': 'success', 'message': 'Working hours deleted'}


@router.post('/{advisor_id}/days-off')
async def add_day_off(
    advisor_id: UUID,
    request: DayOffCreate,
    command_handler: Annotated[
        ScheduleCommandHandler, Depends(get_schedule_command_handler),
    ],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_WRITE))],
) -> dict[str, str]:
    """Add a specific day off."""
    command = AddDayOffCommand(
        advisor_id=advisor_id,
        date=request.date,
        reason=request.reason,
    )
    await command_handler.handle_add_day_off(command)
    return {'status': 'success', 'message': 'Day off added'}


@router.delete('/days-off/{do_id}')
async def delete_day_off(
    do_id: UUID,
    command_handler: Annotated[
        ScheduleCommandHandler, Depends(get_schedule_command_handler),
    ],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_WRITE))],
) -> dict[str, str]:
    """Delete a day off."""
    command = DeleteDayOffCommand(day_off_id=do_id)
    await command_handler.handle_delete_day_off(command)
    return {'status': 'success', 'message': 'Day off deleted'}


@router.get('/leaderboard')
async def get_leaderboard(
    query_handler: Annotated[AdvisorQueryHandler, Depends(get_advisor_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
    time_window: Annotated[
        RankingType,
        Query(
            pattern='^(weekly|monthly|semester|all_time)$',
        ),
    ] = RankingType.ALL_TIME,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PagedResponse[LeaderboardEntryDTO]:
    """Retrieve the advisor leaderboard based on gamification points."""
    query = GetLeaderboardQuery(
        time_window=time_window,
        limit=limit,
        offset=offset,
    )
    return await query_handler.handle_get_leaderboard(query)
