"""Command handlers for advisor schedule management."""

from src.application.dtos.advisor_dtos import (
    AddDayOffCommand,
    AddWorkingHoursCommand,
    DeleteDayOffCommand,
    DeleteWorkingHoursCommand,
    UpdateWorkingHoursCommand,
)
from src.domain.entities.schedule import DayOff, WorkingHours
from src.domain.repositories.schedule_repository import ScheduleRepository


class ScheduleCommandHandler:
    """Handler for schedule-related commands."""

    def __init__(self, schedule_repo: ScheduleRepository):
        self.schedule_repo = schedule_repo

    async def handle_add_working_hours(self, command: AddWorkingHoursCommand) -> None:
        """Add a recurring working hour block."""
        working_hours = WorkingHours(
            advisor_id=command.advisor_id,
            day_of_week=command.day_of_week,
            start_time=command.start_time,
            end_time=command.end_time,
            timezone=command.timezone,
        )
        await self.schedule_repo.add_working_hours(working_hours)

    async def handle_update_working_hours(
        self, command: UpdateWorkingHoursCommand,
    ) -> None:
        """Update an existing working hour block."""
        # 1. Fetch existing entity
        working_hours = await self.schedule_repo.get_working_hours_by_id(
            command.working_hours_id,
        )

        # 2. Perform update via domain entity method
        working_hours.update(
            day_of_week=command.day_of_week,
            start_time=command.start_time,
            end_time=command.end_time,
            timezone=command.timezone,
        )

        # 3. Save
        await self.schedule_repo.update_working_hours(working_hours)

    async def handle_delete_working_hours(
        self,
        command: DeleteWorkingHoursCommand,
    ) -> None:
        """Delete a working hour block."""
        await self.schedule_repo.delete_working_hours(command.working_hours_id)

    async def handle_add_day_off(self, command: AddDayOffCommand) -> None:
        """Add a specific day off."""
        day_off = DayOff(
            advisor_id=command.advisor_id,
            date=command.date,
            reason=command.reason,
        )
        await self.schedule_repo.add_day_off(day_off)

    async def handle_delete_day_off(self, command: DeleteDayOffCommand) -> None:
        """Delete a day off."""
        await self.schedule_repo.delete_day_off(command.day_off_id)
