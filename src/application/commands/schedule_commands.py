"""Command handlers for advisor schedule management."""

from src.application.dtos.advisor_dtos import (
    AddDayOffCommand,
    AddWorkingHoursCommand,
    DeleteDayOffCommand,
    DeleteWorkingHoursCommand,
    UpdateWorkingHoursCommand,
)
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.entities.schedule import DayOff, WorkingHours


class ScheduleCommandHandler:
    """Handler for schedule-related commands."""

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def handle_add_working_hours(self, command: AddWorkingHoursCommand) -> None:
        """Add a recurring working hour block."""
        async with self.uow:
            working_hours = WorkingHours(
                advisor_id=command.advisor_id,
                day_of_week=command.day_of_week,
                start_time=command.start_time,
                end_time=command.end_time,
                timezone=command.timezone,
            )
            await self.uow.schedules.add_working_hours(working_hours)
            await self.uow.commit()

    async def handle_update_working_hours(
        self,
        command: UpdateWorkingHoursCommand,
    ) -> None:
        """Update an existing working hour block."""
        async with self.uow:
            # 1. Fetch existing entity
            working_hours = await self.uow.schedules.get_working_hours_by_id(
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
            await self.uow.schedules.update_working_hours(working_hours)
            await self.uow.commit()

    async def handle_delete_working_hours(
        self,
        command: DeleteWorkingHoursCommand,
    ) -> None:
        """Delete a working hour block."""
        async with self.uow:
            await self.uow.schedules.delete_working_hours(command.working_hours_id)
            await self.uow.commit()

    async def handle_add_day_off(self, command: AddDayOffCommand) -> None:
        """Add a specific day off."""
        async with self.uow:
            day_off = DayOff(
                advisor_id=command.advisor_id,
                date=command.date,
                reason=command.reason,
            )
            await self.uow.schedules.add_day_off(day_off)
            await self.uow.commit()

    async def handle_delete_day_off(self, command: DeleteDayOffCommand) -> None:
        """Delete a day off."""
        async with self.uow:
            await self.uow.schedules.delete_day_off(command.day_off_id)
            await self.uow.commit()
