"""Advisor schedule repository interface."""

from datetime import date
from typing import Protocol
from uuid import UUID

from src.domain.entities.schedule import DayOff, WorkingHours


class ScheduleRepository(Protocol):
    """Interface for managing advisor schedules and days off."""

    async def get_working_hours(self, advisor_id: UUID) -> list[WorkingHours]:
        """Fetch all recurring working hour blocks for an advisor."""
        ...

    async def get_days_off(
        self,
        advisor_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[DayOff]:
        """Fetch specific days off for an advisor within a date range."""
        ...

    async def add_working_hours(self, working_hours: WorkingHours) -> None:
        """Add a new working hour block."""
        ...

    async def add_day_off(self, day_off: DayOff) -> None:
        """Add a new day off."""
        ...
