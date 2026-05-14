"""Unit tests for the SQLAlchemy Unit of Work implementation."""

import pickle
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.case import Case
from src.domain.entities.student import Student
from src.domain.value_objects.status import InterventionStatus, OutboxStatus, RiskStatus
from src.infrastructure.database.models import OutboxEvent
from src.infrastructure.database.models import Student as StudentOrm
from src.infrastructure.persistence.sqlalchemy_uow import SqlAlchemyUnitOfWork


@pytest.mark.asyncio
async def test_uow_commit_persists_data(
    test_db_session: AsyncSession,
    uow: SqlAlchemyUnitOfWork,
) -> None:
    """Verify that commit() persists repository changes to the database."""
    sid = uuid.uuid4()
    student = Student(
        sid=sid,
        student_name="Test Student",
        email="test@example.com",
        major="Computer Science",
        last_notified_timestamp=None,
        current_risk_status=RiskStatus.NORMAL,
        last_notified_satisfaction=None,
    )

    async with uow:
        # We need to use ingest or manual ORM add since Student table is likely empty
        # But let's assume we use the repository save which currently expects an existing record
        # for update. Let's use ingest_students for initial setup or just add to session.
        test_db_session.add(StudentOrm(
            sid=sid,
            student_name="Old Name",
            email="test@example.com",
            major="CS",
            current_risk_status="Normal"
        ))
        await test_db_session.flush()

        # Update via UoW
        student_domain = await uow.students.get_by_id(sid)
        student_domain.student_name = "Updated Name"
        await uow.students.save(student_domain)
        await uow.commit()

    # Verify persistence
    result = await test_db_session.execute(
        select(StudentOrm).where(StudentOrm.sid == sid)
    )
    persisted = result.scalar_one()
    assert persisted.student_name == "Updated Name"


@pytest.mark.asyncio
async def test_uow_rollback_cancels_changes(
    test_db_session: AsyncSession,
    uow: SqlAlchemyUnitOfWork,
) -> None:
    """Verify that rollback() (or exception) cancels repository changes."""
    sid = uuid.uuid4()
    test_db_session.add(StudentOrm(
        sid=sid,
        student_name="Original Name",
        email="test@example.com",
        major="CS",
        current_risk_status="Normal"
    ))
    await test_db_session.commit()

    try:
        async with uow:
            student = await uow.students.get_by_id(sid)
            student.student_name = "Should Not Save"
            await uow.students.save(student)
            raise ValueError("Forced error")
    except ValueError:
        pass

    # Verify it was NOT updated
    result = await test_db_session.execute(
        select(StudentOrm).where(StudentOrm.sid == sid)
    )
    persisted = result.scalar_one()
    assert persisted.student_name == "Original Name"


@pytest.mark.asyncio
async def test_uow_extracts_and_persists_events(
    test_db_session: AsyncSession,
    uow: SqlAlchemyUnitOfWork,
) -> None:
    """Verify that domain events are extracted and saved as outbox events on commit."""
    case_id = uuid.uuid4()
    sid = uuid.uuid4()
    advisor_id = uuid.uuid4()
    occurred_at = datetime.now(UTC)

    # Setup case
    case = Case(
        sid=sid,
        case_id=case_id,
        intervention_status=InterventionStatus.NEW,
        version=0
    )
    
    async with uow:
        await uow.cases.add(case) # This registers the entity
        
        # Trigger an event
        case.assign_advisor(advisor_id, occurred_at)
        
        await uow.commit()

    # Verify outbox event exists
    result = await test_db_session.execute(select(OutboxEvent))
    events = result.scalars().all()
    
    assert len(events) >= 1
    # CaseAcceptedEvent should be mapped to run_case_accepted_task and websocket_broadcast
    task_names = [e.task_name for e in events]
    assert "run_case_accepted_task" in task_names
    assert "websocket_broadcast" in task_names
    
    # Check payload of run_case_accepted_task
    bg_event = next(e for e in events if e.task_name == "run_case_accepted_task")
    payload = pickle.loads(bg_event.payload)
    assert payload["case_id"] == case_id
    assert payload["advisor_id"] == advisor_id
    assert bg_event.status == OutboxStatus.PENDING


@pytest.mark.asyncio
async def test_uow_clears_events_after_commit(
    uow: SqlAlchemyUnitOfWork,
) -> None:
    """Verify that entity event buffer is cleared after UoW commit."""
    case = Case(sid=uuid.uuid4(), intervention_status=InterventionStatus.NEW)
    case.register_event(uuid.uuid4()) # Dummy event
    
    async with uow:
        uow.collect_events(case)
        assert len(case.domain_events) == 1
        await uow.commit()
        
    assert len(case.domain_events) == 0


@pytest.mark.asyncio
async def test_uow_multiple_entities_multiple_events(
    test_db_session: AsyncSession,
    uow: SqlAlchemyUnitOfWork,
) -> None:
    """Verify that events from multiple entities are collected and saved."""
    case1 = Case(sid=uuid.uuid4(), case_id=uuid.uuid4(), intervention_status=InterventionStatus.NEW)
    case2 = Case(sid=uuid.uuid4(), case_id=uuid.uuid4(), intervention_status=InterventionStatus.NEW)
    
    async with uow:
        await uow.cases.add(case1)
        await uow.cases.add(case2)
        
        # Trigger events on both
        case1.assign_advisor(uuid.uuid4(), datetime.now(UTC))
        case2.assign_advisor(uuid.uuid4(), datetime.now(UTC))
        
        await uow.commit()

    # Verify outbox events
    result = await test_db_session.execute(select(OutboxEvent))
    events = result.scalars().all()
    
    # Each CaseAcceptedEvent produces 2 tasks (bg + ws), so 4 total
    assert len(events) == 4
    task_names = [e.task_name for e in events]
    assert task_names.count("run_case_accepted_task") == 2
    assert task_names.count("websocket_broadcast") == 2


@pytest.mark.asyncio
async def test_uow_rollback_cancels_outbox_events(
    test_db_session: AsyncSession,
    uow: SqlAlchemyUnitOfWork,
) -> None:
    """Verify that no outbox event is added if the transaction rolls back."""
    async with uow:
        await uow.enqueue("test_task", arg="val")
        # Simulate failure before commit
        await uow.rollback()
        
    result = await test_db_session.execute(select(OutboxEvent))
    events = result.scalars().all()
    assert len(events) == 0


@pytest.mark.asyncio
async def test_uow_enqueue_manual_task(
    test_db_session: AsyncSession,
    uow: SqlAlchemyUnitOfWork,
) -> None:
    """Verify that enqueue() adds a manual task to the outbox."""
    async with uow:
        await uow.enqueue("manual_task", arg1="val1", arg2=123)
        await uow.commit()
        
    result = await test_db_session.execute(
        select(OutboxEvent).where(OutboxEvent.task_name == "manual_task")
    )
    event = result.scalar_one()
    payload = pickle.loads(event.payload)
    assert payload == {"arg1": "val1", "arg2": 123}
