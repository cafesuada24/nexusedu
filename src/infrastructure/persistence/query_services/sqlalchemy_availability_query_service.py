"""SQLAlchemy implementation of the AdvisorAvailabilityQueryService."""

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.advisor_dtos import (
    AdvisorScheduleDTO,
    DayOffDTO,
    WorkingHoursDTO,
)
from src.application.interfaces.availability_query_service import (
    AdvisorAvailabilityQueryService,
)
from src.infrastructure.database.models import (
    AdvisorDayOff,
    AdvisorWorkingHours,
    Appointment,
)
from src.infrastructure.database.models import (
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
        wh_stmt = select(AdvisorWorkingHours).where(
            AdvisorWorkingHours.advisor_id == advisor_id,
        )
        wh_result = await self.session.execute(wh_stmt)
        working_hours = wh_result.scalars().all()

        if not working_hours:
            return []

        # 2. Fetch Days Off
        do_stmt = select(AdvisorDayOff.date).where(
            AdvisorDayOff.advisor_id == advisor_id,
            AdvisorDayOff.date >= start_date,
            AdvisorDayOff.date <= end_date,
        )
        do_result = await self.session.execute(do_stmt)
        days_off_dates = set(do_result.scalars().all())

        # 3. Fetch Booked Appointments
        # Pad range by 1 day to safely cover timezone overlaps
        app_stmt = (
            select(Appointment.appointment_time, Appointment.duration_minutes)
            .join(OrmCase, OrmCase.case_id == Appointment.case_id)
            .where(
                OrmCase.assigned_advisor_id == advisor_id,
                Appointment.appointment_time
                >= datetime.combine(start_date - timedelta(days=1), time.min, tzinfo=UTC),
                Appointment.appointment_time
                <= datetime.combine(end_date + timedelta(days=1), time.max, tzinfo=UTC),
            )
        )
        app_result = await self.session.execute(app_stmt)
        # Store as (start_utc, duration)
        booked_appointments = [
            (row[0].astimezone(UTC), row[1]) for row in app_result.all()
        ]

        # 4. Generate Slots
        available_slots: list[datetime] = []
        current_date = start_date
        now_utc = datetime.now(UTC)

        while current_date <= end_date:
            if current_date in days_off_dates:
                current_date += timedelta(days=1)
                continue

            day_of_week = current_date.weekday()
            day_schedules = [
                wh for wh in working_hours if wh.day_of_week == day_of_week
            ]

            for wh in day_schedules:
                tz = ZoneInfo(wh.timezone)
                local_start = datetime.combine(current_date, wh.start_time, tzinfo=tz)
                local_end = datetime.combine(current_date, wh.end_time, tzinfo=tz)

                # Handle cross-midnight shifts
                if wh.end_time <= wh.start_time:
                    local_end += timedelta(days=1)

                cursor = local_start
                while cursor + timedelta(minutes=slot_duration_minutes) <= local_end:
                    utc_slot_start = cursor.astimezone(UTC)
                    utc_slot_end = utc_slot_start + timedelta(
                        minutes=slot_duration_minutes,
                    )

                    if utc_slot_start > now_utc:
                        # Check for overlaps with any booked appointment
                        is_booked = False
                        for b_start, b_duration in booked_appointments:
                            b_end = b_start + timedelta(minutes=b_duration)
                            # Overlap: max(start1, start2) < min(end1, end2)
                            if max(utc_slot_start, b_start) < min(utc_slot_end, b_end):
                                is_booked = True
                                break

                        if not is_booked:
                            available_slots.append(utc_slot_start)

                    cursor += timedelta(minutes=slot_duration_minutes)

            current_date += timedelta(days=1)

        return sorted(available_slots)

    async def get_advisor_schedule(self, advisor_id: UUID) -> AdvisorScheduleDTO:
        """Fetch the full schedule directly from the database."""
        # 1. Fetch Working Hours
        wh_stmt = select(AdvisorWorkingHours).where(
            AdvisorWorkingHours.advisor_id == advisor_id,
        )
        wh_result = await self.session.execute(wh_stmt)
        working_hours = wh_result.scalars().all()

        # 2. Fetch Days Off (e.g., next 3 months)
        do_stmt = select(AdvisorDayOff).where(
            AdvisorDayOff.advisor_id == advisor_id,
            AdvisorDayOff.date >= date.today(),
            AdvisorDayOff.date <= date.today() + timedelta(days=90),
        )
        do_result = await self.session.execute(do_stmt)
        days_off = do_result.scalars().all()

        return AdvisorScheduleDTO(
            working_hours=[
                WorkingHoursDTO(
                    id=wh.id,
                    day_of_week=wh.day_of_week,
                    start_time=wh.start_time,
                    end_time=wh.end_time,
                    timezone=wh.timezone,
                )
                for wh in working_hours
            ],
            days_off=[
                DayOffDTO(id=do.id, date=do.date, reason=do.reason) for do in days_off
            ],
        )
