"""Advisor availability domain service (Command Side)."""

from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.schedule_repository import ScheduleRepository


class AdvisorAvailabilityService:
    """Domain service to enforce advisor availability invariants."""

    def __init__(
        self,
        schedule_repo: ScheduleRepository,
        case_repo: CaseRepository,
    ):
        self.schedule_repo = schedule_repo
        self.case_repo = case_repo

    async def is_slot_available(
        self,
        advisor_id: UUID,
        requested_time: datetime,
    ) -> bool:
        """Check if a specific UTC time slot is valid and available for booking."""
        requested_utc = requested_time.astimezone(UTC)
        if requested_utc < datetime.now(UTC):
            return False

        # 1. Check if the slot is within working hours
        working_hours = await self.schedule_repo.get_working_hours(advisor_id)
        day_of_week = requested_utc.weekday()

        # We need to find if any working hour block matches the local time of the advisor
        # For simplicity, we check if the advisor has ANY working hours defined first.
        # If no hours defined, we assume unavailable (as per new robust rule).
        if not working_hours:
            return False

        is_within_hours = False
        for wh in working_hours:
            if wh.day_of_week == day_of_week:
                tz = ZoneInfo(wh.timezone)
                local_req = requested_utc.astimezone(tz)
                if wh.start_time <= local_req.time() < wh.end_time:
                    is_within_hours = True
                    break

        if not is_within_hours:
            return False

        # 2. Check for Day Off
        days_off = await self.schedule_repo.get_days_off(
            advisor_id,
            requested_utc.date(),
            requested_utc.date(),
        )
        if days_off:
            return False

        # 3. Check for double booking
        has_conflict = await self.case_repo.has_overlapping_appointment(
            advisor_id,
            requested_utc,
        )

        return not has_conflict
