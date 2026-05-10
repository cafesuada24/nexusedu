"""SQLAlchemy implementation of the AdvisorAvailabilityQueryService."""

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.availability_query_service import AdvisorAvailabilityQueryService
from src.infrastructure.database.models import (
    AdvisorDayOff,
    AdvisorWorkingHours,
    Appointment,
    Case as OrmCase,
)


class SqlAlchemyAdvisorAvailabilityQueryService(AdvisorAvailabilityQueryService):
    """Calculates available slots using direct database projections."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_available_slots(
        self,
        advisor_id: UUID,
        start_date: date,
        end_date: date,
        slot_duration_minutes: int = 30,
    ) -> list[datetime]:
        """Directly calculate available UTC timeslots."""
        
        # 1. Fetch Working Hours
        wh_stmt = (
            select(AdvisorWorkingHours)
            .where(AdvisorWorkingHours.advisor_id == advisor_id)
        )
        wh_result = await self.session.execute(wh_stmt)
        working_hours = wh_result.scalars().all()
        
        if not working_hours:
            return []

        # 2. Fetch Days Off
        do_stmt = (
            select(AdvisorDayOff.date)
            .where(
                AdvisorDayOff.advisor_id == advisor_id,
                AdvisorDayOff.date >= start_date,
                AdvisorDayOff.date <= end_date,
            )
        )
        do_result = await self.session.execute(do_stmt)
        days_off_dates = set(do_result.scalars().all())

        # 3. Fetch Booked Appointments
        # We join with OrmCase because advisor_id is on Case
        app_stmt = (
            select(Appointment.appointment_time)
            .join(OrmCase, OrmCase.case_id == Appointment.case_id)
            .where(
                OrmCase.assigned_advisor_id == advisor_id,
                Appointment.appointment_time >= datetime.combine(start_date, time.min, tzinfo=UTC),
                Appointment.appointment_time <= datetime.combine(end_date, time.max, tzinfo=UTC),
            )
        )
        app_result = await self.session.execute(app_stmt)
        booked_times = {t.astimezone(UTC) for t in app_result.scalars().all()}

        # 4. Generate Slots
        available_slots: list[datetime] = []
        current_date = start_date
        now_utc = datetime.now(UTC)

        while current_date <= end_date:
            if current_date in days_off_dates:
                current_date += timedelta(days=1)
                continue

            day_of_week = current_date.weekday()
            day_schedules = [wh for wh in working_hours if wh.day_of_week == day_of_week]

            for wh in day_schedules:
                tz = ZoneInfo(wh.timezone)
                local_start = datetime.combine(current_date, wh.start_time, tzinfo=tz)
                local_end = datetime.combine(current_date, wh.end_time, tzinfo=tz)

                cursor = local_start
                while cursor + timedelta(minutes=slot_duration_minutes) <= local_end:
                    utc_slot = cursor.astimezone(UTC)
                    if utc_slot not in booked_times and utc_slot > now_utc:
                        available_slots.append(utc_slot)
                    cursor += timedelta(minutes=slot_duration_minutes)

            current_date += timedelta(days=1)

        return sorted(available_slots)
