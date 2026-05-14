"""Unit tests for ScheduleCommandHandler."""

import uuid
from datetime import date, time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.commands.schedule_commands import (
    AddDayOffCommand,
    AddWorkingHoursCommand,
    DeleteDayOffCommand,
    DeleteWorkingHoursCommand,
    ScheduleCommandHandler,
    UpdateWorkingHoursCommand,
)
from src.domain.entities.schedule import WorkingHours


@pytest.fixture
def mock_uow():
    uow = MagicMock()
    uow.schedules = AsyncMock()
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    return uow


@pytest.fixture
def handler(mock_uow):
    return ScheduleCommandHandler(uow=mock_uow)


@pytest.mark.asyncio
async def test_handle_add_working_hours(handler, mock_uow):
    advisor_id = uuid.uuid4()
    command = AddWorkingHoursCommand(
        advisor_id=advisor_id,
        day_of_week=0,
        start_time=time(9, 0),
        end_time=time(17, 0),
        timezone="UTC"
    )

    await handler.handle_add_working_hours(command)

    mock_uow.schedules.add_working_hours.assert_called_once()
    mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_update_working_hours(handler, mock_uow):
    wh_id = uuid.uuid4()
    advisor_id = uuid.uuid4()
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
    mock_uow.schedules.get_working_hours_by_id.return_value = existing_wh

    await handler.handle_update_working_hours(command)

    mock_uow.schedules.get_working_hours_by_id.assert_called_once_with(wh_id)
    mock_uow.schedules.update_working_hours.assert_called_once()
    mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_delete_working_hours(handler, mock_uow):
    wh_id = uuid.uuid4()
    command = DeleteWorkingHoursCommand(working_hours_id=wh_id)

    await handler.handle_delete_working_hours(command)

    mock_uow.schedules.delete_working_hours.assert_called_once_with(wh_id)
    mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_add_day_off(handler, mock_uow):
    advisor_id = uuid.uuid4()
    command = AddDayOffCommand(advisor_id=advisor_id, date=date(2026, 6, 1), reason="Vacation")

    await handler.handle_add_day_off(command)

    mock_uow.schedules.add_day_off.assert_called_once()
    mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_delete_day_off(handler, mock_uow):
    do_id = uuid.uuid4()
    command = DeleteDayOffCommand(day_off_id=do_id)

    await handler.handle_delete_day_off(command)

    mock_uow.schedules.delete_day_off.assert_called_once_with(do_id)
    mock_uow.commit.assert_called_once()
