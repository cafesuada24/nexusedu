"""Unit tests for AdvisorAvailabilityService (Command Side)."""

from datetime import UTC, datetime, time
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.domain.entities.schedule import DayOff, WorkingHours
from src.domain.services.availability import AdvisorAvailabilityService


@pytest.fixture
def schedule_repo():
    return AsyncMock()


@pytest.fixture
def case_repo():
    return AsyncMock()


@pytest.fixture
def availability_service(schedule_repo, case_repo):
    return AdvisorAvailabilityService(schedule_repo, case_repo)


@pytest.mark.asyncio
async def test_is_slot_available_success(availability_service, schedule_repo, case_repo):
    # Setup
    advisor_id = uuid4()
    requested_time = datetime(2026, 5, 11, 9, 0, tzinfo=UTC)  # Monday
    
    schedule_repo.get_working_hours.return_value = [
        WorkingHours(advisor_id=advisor_id, day_of_week=0, start_time=time(9, 0), end_time=time(17, 0), timezone="UTC"),
    ]
    schedule_repo.get_days_off.return_value = []
    case_repo.has_overlapping_appointment.return_value = False

    # Execute
    result = await availability_service.is_slot_available(advisor_id, requested_time)

    # Verify
    assert result is True


@pytest.mark.asyncio
async def test_is_slot_available_outside_hours(availability_service, schedule_repo, case_repo):
    # Setup
    advisor_id = uuid4()
    requested_time = datetime(2026, 5, 11, 8, 30, tzinfo=UTC)  # Monday 8:30 (starts at 9)
    
    schedule_repo.get_working_hours.return_value = [
        WorkingHours(advisor_id=advisor_id, day_of_week=0, start_time=time(9, 0), end_time=time(17, 0), timezone="UTC"),
    ]
    schedule_repo.get_days_off.return_value = []

    # Execute
    result = await availability_service.is_slot_available(advisor_id, requested_time)

    # Verify
    assert result is False


@pytest.mark.asyncio
async def test_is_slot_available_day_off(availability_service, schedule_repo, case_repo):
    # Setup
    advisor_id = uuid4()
    requested_time = datetime(2026, 5, 11, 10, 0, tzinfo=UTC)
    
    schedule_repo.get_working_hours.return_value = [
        WorkingHours(advisor_id=advisor_id, day_of_week=0, start_time=time(9, 0), end_time=time(17, 0), timezone="UTC"),
    ]
    schedule_repo.get_days_off.return_value = [DayOff(advisor_id=advisor_id, date=requested_time.date())]

    # Execute
    result = await availability_service.is_slot_available(advisor_id, requested_time)

    # Verify
    assert result is False


@pytest.mark.asyncio
async def test_is_slot_available_conflict(availability_service, schedule_repo, case_repo):
    # Setup
    advisor_id = uuid4()
    requested_time = datetime(2026, 5, 11, 10, 0, tzinfo=UTC)
    
    schedule_repo.get_working_hours.return_value = [
        WorkingHours(advisor_id=advisor_id, day_of_week=0, start_time=time(9, 0), end_time=time(17, 0), timezone="UTC"),
    ]
    schedule_repo.get_days_off.return_value = []
    case_repo.has_overlapping_appointment.return_value = True

    # Execute
    result = await availability_service.is_slot_available(advisor_id, requested_time)

    # Verify
    assert result is False
