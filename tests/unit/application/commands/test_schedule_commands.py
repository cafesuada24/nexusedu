"""Unit tests for ScheduleCommandHandler."""

from datetime import date, time
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.commands.schedule_commands import ScheduleCommandHandler
from src.application.dtos.advisor_dtos import (
    AddDayOffCommand,
    AddWorkingHoursCommand,
    DeleteDayOffCommand,
    DeleteWorkingHoursCommand,
    UpdateWorkingHoursCommand,
)
from src.domain.entities.schedule import DayOff, WorkingHours


@pytest.fixture
def schedule_repo():
    return AsyncMock()


@pytest.fixture
def handler(schedule_repo):
    return ScheduleCommandHandler(schedule_repo)


@pytest.mark.asyncio
async def test_handle_add_working_hours(handler, schedule_repo):
    advisor_id = uuid4()
    command = AddWorkingHoursCommand(
        advisor_id=advisor_id,
        day_of_week=0,
        start_time=time(9, 0),
        end_time=time(17, 0),
        timezone="UTC"
    )
    
    await handler.handle_add_working_hours(command)
    
    schedule_repo.add_working_hours.assert_called_once()
    wh = schedule_repo.add_working_hours.call_args[0][0]
    assert isinstance(wh, WorkingHours)
    assert wh.advisor_id == advisor_id
    assert wh.day_of_week == 0
    assert wh.start_time == time(9, 0)


@pytest.mark.asyncio
async def test_handle_update_working_hours(handler, schedule_repo):
    wh_id = uuid4()
    advisor_id = uuid4()
    command = UpdateWorkingHoursCommand(
        working_hours_id=wh_id,
        day_of_week=1,
        start_time=time(10, 0),
        end_time=time(15, 0),
        timezone="EST"
    )

    # Mock return value as a real entity
    existing_wh = WorkingHours(
        id=wh_id,
        advisor_id=advisor_id,
        day_of_week=0,
        start_time=time(9, 0),
        end_time=time(17, 0),
        timezone="UTC"
    )
    schedule_repo.get_working_hours_by_id.return_value = existing_wh

    await handler.handle_update_working_hours(command)

    schedule_repo.get_working_hours_by_id.assert_called_once_with(wh_id)
    schedule_repo.update_working_hours.assert_called_once()
    wh = schedule_repo.update_working_hours.call_args[0][0]
    assert wh.id == wh_id
    assert wh.day_of_week == 1
    assert wh.timezone == "EST"
    assert wh.advisor_id == advisor_id

@pytest.mark.asyncio
async def test_handle_delete_working_hours(handler, schedule_repo):
    wh_id = uuid4()
    command = DeleteWorkingHoursCommand(working_hours_id=wh_id)
    
    await handler.handle_delete_working_hours(command)
    
    schedule_repo.delete_working_hours.assert_called_once_with(wh_id)


@pytest.mark.asyncio
async def test_handle_add_day_off(handler, schedule_repo):
    advisor_id = uuid4()
    command = AddDayOffCommand(advisor_id=advisor_id, date=date(2026, 6, 1), reason="Vacation")
    
    await handler.handle_add_day_off(command)
    
    schedule_repo.add_day_off.assert_called_once()
    do = schedule_repo.add_day_off.call_args[0][0]
    assert isinstance(do, DayOff)
    assert do.advisor_id == advisor_id
    assert do.date == date(2026, 6, 1)


@pytest.mark.asyncio
async def test_handle_delete_day_off(handler, schedule_repo):
    do_id = uuid4()
    command = DeleteDayOffCommand(day_off_id=do_id)
    
    await handler.handle_delete_day_off(command)
    
    schedule_repo.delete_day_off.assert_called_once_with(do_id)


@pytest.mark.asyncio
async def test_invalid_working_hours_rejected(handler):
    with pytest.raises(ValueError, match="start_time must be before end_time"):
        AddWorkingHoursCommand(
            advisor_id=uuid4(),
            day_of_week=0,
            start_time=time(17, 0),
            end_time=time(9, 0), # Invalid: end before start
        )
