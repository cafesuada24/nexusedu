"""Exhaustive tests for AdvisorAvailabilityService edge cases."""

from datetime import UTC, datetime, time
from unittest.mock import AsyncMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from src.domain.entities.schedule import WorkingHours
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
async def test_cross_midnight_shift_early_morning(availability_service, schedule_repo, case_repo):
    """Test a 22:00-06:00 shift where requested time is 01:00 the next day."""
    advisor_id = uuid4()
    # Monday 22:00 - Tuesday 06:00
    # Requested: Tuesday May 11, 2027 01:00 UTC
    requested_time = datetime(2027, 5, 11, 1, 0, tzinfo=UTC) 
    
    schedule_repo.get_working_hours.return_value = [
        # Monday shift
        WorkingHours(advisor_id=advisor_id, day_of_week=0, start_time=time(22, 0), end_time=time(6, 0), timezone="UTC"),
    ]
    schedule_repo.get_days_off.return_value = []
    case_repo.has_overlapping_appointment.return_value = False

    result = await availability_service.is_slot_available(advisor_id, requested_time)
    assert result is True


@pytest.mark.asyncio
async def test_cross_midnight_shift_late_night(availability_service, schedule_repo, case_repo):
    """Test a 22:00-06:00 shift where requested time is 23:00 same day."""
    advisor_id = uuid4()
    # Monday May 10, 2027
    requested_time = datetime(2027, 5, 10, 23, 0, tzinfo=UTC) 
    
    schedule_repo.get_working_hours.return_value = [
        WorkingHours(advisor_id=advisor_id, day_of_week=0, start_time=time(22, 0), end_time=time(6, 0), timezone="UTC"),
    ]
    schedule_repo.get_days_off.return_value = []
    case_repo.has_overlapping_appointment.return_value = False

    result = await availability_service.is_slot_available(advisor_id, requested_time)
    assert result is True


@pytest.mark.asyncio
async def test_timezone_conversion_correct_day(availability_service, schedule_repo, case_repo):
    """Test that timezone conversion correctly identifies the advisor's local day."""
    advisor_id = uuid4()
    # Advisor in Tokyo (UTC+9). 
    # Requested: Monday May 10, 2027 00:30 UTC. 
    # Local Tokyo: Monday 09:30.
    requested_time = datetime(2027, 5, 10, 0, 30, tzinfo=UTC) 
    
    schedule_repo.get_working_hours.return_value = [
        # Monday shift in Tokyo
        WorkingHours(advisor_id=advisor_id, day_of_week=0, start_time=time(9, 0), end_time=time(17, 0), timezone="Asia/Tokyo"),
    ]
    schedule_repo.get_days_off.return_value = []
    case_repo.has_overlapping_appointment.return_value = False

    result = await availability_service.is_slot_available(advisor_id, requested_time)
    assert result is True


@pytest.mark.asyncio
async def test_timezone_conversion_wrong_day(availability_service, schedule_repo, case_repo):
    """Test that timezone conversion correctly identifies if it's NOT the advisor's working day."""
    advisor_id = uuid4()
    # Advisor in Tokyo (UTC+9). 
    # Requested: Sunday 21:00 UTC. 
    # Local Tokyo: Monday 06:00. (Outside 09:00-17:00 shift)
    requested_time = datetime(2027, 5, 10, 21, 0, tzinfo=UTC) 
    
    schedule_repo.get_working_hours.return_value = [
        WorkingHours(advisor_id=advisor_id, day_of_week=0, start_time=time(9, 0), end_time=time(17, 0), timezone="Asia/Tokyo"),
    ]
    schedule_repo.get_days_off.return_value = []
    case_repo.has_overlapping_appointment.return_value = False

    result = await availability_service.is_slot_available(advisor_id, requested_time)
    assert result is False
