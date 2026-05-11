"""Advisor schedule repository interface."""

from datetime import date
from typing import Protocol

from src.core.identifiers import EntityID
from src.domain.entities.schedule import DayOff, WorkingHours


class ScheduleRepository(Protocol):
    """Interface for managing advisor schedules and days off."""

    async def get_working_hours(self, advisor_id: EntityID) -> list[WorkingHours]:
        """Fetch all recurring working hour blocks for an advisor."""
        ...

    async def get_working_hours_by_id(self, wh_id: EntityID) -> WorkingHours:
        """Fetch a specific working hour block. Raises WorkingHoursNotFoundError if not found."""
        ...

    async def get_days_off(
        self,
        advisor_id: EntityID,
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

    async def update_working_hours(self, working_hours: WorkingHours) -> None:
        """Update an existing working hour block."""
        ...

    async def delete_working_hours(self, wh_id: EntityID) -> None:
        """Delete a working hour block."""
        ...

    async def delete_day_off(self, do_id: EntityID) -> None:
        """Delete a day off."""
        ...
