"""Advisor availability domain service (Command Side)."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from src.core.identifiers import EntityID
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
        advisor_id: EntityID,
        requested_time: datetime,
        duration_minutes: int = 30,
    ) -> bool:
        """Check if a specific UTC time slot is valid and available for booking."""
        requested_utc = requested_time.astimezone(UTC)
        if requested_utc < datetime.now(UTC):
            return False

        # 1. Check if the slot is within working hours
        working_hours = await self.schedule_repo.get_working_hours(advisor_id)
        if not working_hours:
            return False

        is_within_hours = False
        for wh in working_hours:
            tz = ZoneInfo(wh.timezone)
            local_req = requested_utc.astimezone(tz)
            local_time = local_req.time()
            local_weekday = local_req.weekday()

            # Check if this working hour block applies to the local weekday
            if wh.day_of_week == local_weekday:
                if wh.start_time < wh.end_time:
                    # Normal shift
                    if wh.start_time <= local_time < wh.end_time:
                        is_within_hours = True
                        break
                # Cross-midnight shift (e.g., 22:00 - 06:00)
                # If local time is >= 22:00, it's the start part of the shift on the same day.
                elif local_time >= wh.start_time:
                    is_within_hours = True
                    break

            # Also check if this is the "tail" end of a cross-midnight shift from the PREVIOUS day
            # If local time is < 06:00, it's the tail part of the shift from yesterday.
            previous_weekday = (local_weekday - 1) % 7
            if (
                wh.day_of_week == previous_weekday
                and wh.start_time >= wh.end_time
                and local_time < wh.end_time
            ):
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
            duration_minutes=duration_minutes,
        )

        return not has_conflict
