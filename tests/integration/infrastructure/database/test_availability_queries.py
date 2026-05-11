from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.value_objects.status import MeetingMethod
from src.infrastructure.database.models import (
    Advisor,
    AdvisorWorkingHours,
    Appointment,
    Base,
    Case,
    Student,
)
from src.infrastructure.persistence.query_services.sqlalchemy_availability_query_service import (
    SqlAlchemyAdvisorAvailabilityQueryService,
)


@pytest.fixture
async def session():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_available_slots_interval_overlap(session: AsyncSession):
    """Test that slots are correctly rejected if they overlap with an appointment (interval check)."""
    query_service = SqlAlchemyAdvisorAvailabilityQueryService(session)

    advisor_id = uuid4()
    student_id = uuid4()
    case_id = uuid4()

    # 1. Setup Data
    advisor = Advisor(
        advisor_id=advisor_id, name='Test Advisor', email='advisor@test.com'
    )
    student = Student(
        sid=student_id,
        student_name='Test Student',
        email='student@test.com',
        major='CS',
    )
    case = Case(case_id=case_id, sid=student_id, assigned_advisor_id=advisor_id)

    # Advisor works 09:00 - 17:00 on Monday May 10, 2027
    wh = AdvisorWorkingHours(
        advisor_id=advisor_id,
        day_of_week=0,  # Monday
        start_time=time(9, 0),
        end_time=time(17, 0),
        timezone='UTC',
    )

    # Booked appointment at 09:15 for 45 minutes (ends at 10:00)
    # This should overlap with 09:00-09:30 and 09:30-10:00 slots.
    appointment = Appointment(
        case_id=case_id,
        appointment_time=datetime(2027, 5, 10, 9, 15, tzinfo=UTC),
        duration_minutes=45,
        meeting_method=MeetingMethod.ONLINE,
    )

    session.add_all([advisor, student, case, wh, appointment])
    await session.commit()

    # 2. Execute
    start_date = date(2027, 5, 10)
    end_date = date(2027, 5, 10)
    slots = await query_service.get_available_slots(advisor_id, start_date, end_date)

    # 3. Verify
    # Slots are generated every 30 minutes: 09:00, 09:30, 10:00, 10:30, ...
    # 09:00-09:30 overlaps with 09:15-10:00
    # 09:30-10:00 overlaps with 09:15-10:00
    # 10:00-10:30 should be available.
    slot_times = [s.time() for s in slots]
    assert time(9, 0) not in slot_times
    assert time(9, 30) not in slot_times
    assert time(10, 0) in slot_times


@pytest.mark.asyncio
async def test_get_available_slots_cross_midnight(session: AsyncSession):
    """Test that slots are correctly generated for cross-midnight shifts."""
    query_service = SqlAlchemyAdvisorAvailabilityQueryService(session)
    advisor_id = uuid4()

    wh = AdvisorWorkingHours(
        advisor_id=advisor_id,
        day_of_week=0,  # Monday
        start_time=time(22, 0),
        end_time=time(2, 0),  # To Tuesday 02:00
        timezone='UTC',
    )
    session.add(wh)
    await session.commit()

    start_date = date(2027, 5, 10)  # Monday
    end_date = date(2027, 5, 10)
    slots = await query_service.get_available_slots(advisor_id, start_date, end_date)

    # Monday 22:00, 22:30, 23:00, 23:30, Tuesday 00:00, 00:30, 01:00, 01:30
    assert len(slots) == 8
    slot_times = [s.time() for s in slots]
    assert time(22, 0) in slot_times
    assert time(23, 30) in slot_times
    assert time(0, 0) in slot_times
    assert time(1, 30) in slot_times
