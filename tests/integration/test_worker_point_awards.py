import pytest
from datetime import datetime, UTC, timedelta
from uuid import uuid4
from sqlalchemy import select
from src.domain.entities.case import Case
from src.domain.value_objects.status import RiskStatus, InterventionStatus
from src.infrastructure.database.models import Advisor, PointLedger, Student, InterventionEmail
from src.worker import (
    run_case_accepted_task,
    run_dispatch_email_task,
    run_student_booked_task,
    run_case_resolved_task,
)

@pytest.fixture
async def setup_data(test_db_session, mock_user):
    sid = uuid4()
    advisor_id = uuid4()
    
    # 1. Create Student
    student = Student(
        sid=sid,
        student_name="Test Student",
        email="student@test.com",
        current_risk_status="Critical"
    )
    test_db_session.add(student)
    
    # 2. Create Advisor
    advisor = Advisor(
        advisor_id=advisor_id,
        user_id=mock_user.id,
        name="Test Advisor",
        email="advisor@test.com"
    )
    test_db_session.add(advisor)
    await test_db_session.commit()
    
    return sid, advisor_id

@pytest.mark.asyncio
async def test_run_case_accepted_task_points(test_db_session, setup_data, monkeypatch):
    sid, advisor_id = setup_data
    case_id = uuid4()
    
    # Create a case created 1 hour ago
    created_at = datetime.now(UTC) - timedelta(hours=1)
    case = Case(case_id=case_id, sid=sid, created_at=created_at)
    # Using the repository to ensure it's in DB
    from src.infrastructure.persistence.repositories.sqlalchemy_repositories import SqlAlchemyCaseRepository
    repo = SqlAlchemyCaseRepository(test_db_session)
    await repo.add(case)
    await test_db_session.commit()

    # Mock get_async_session to return our test_db_session
    async def mock_get_async_session():
        yield test_db_session
    monkeypatch.setattr("src.worker.get_async_session", mock_get_async_session)

    # Act
    occurred_at = datetime.now(UTC)
    await run_case_accepted_task({}, case_id, advisor_id, occurred_at)

    # Assert: 5 base * 1.0 risk * 1.5 SLA (<12h) = 7 points
    stmt = select(PointLedger).where(PointLedger.case_id == case_id, PointLedger.action == "accept_case")
    result = await test_db_session.execute(stmt)
    entry = result.scalar_one()
    assert entry.points == 7

@pytest.mark.asyncio
async def test_run_dispatch_email_task_points(test_db_session, setup_data, monkeypatch):
    sid, advisor_id = setup_data
    case_id = uuid4()
    
    # Case assigned 1 hour ago
    assigned_at = datetime.now(UTC) - timedelta(hours=1)
    case = Case(case_id=case_id, sid=sid, assigned_advisor_id=advisor_id, assigned_at=assigned_at)
    case.intervention_status = InterventionStatus.ACCEPTED
    
    # Need an email record
    email = InterventionEmail(case_id=case_id, status="draft", subject="S", body="B")
    test_db_session.add(email)

    from src.infrastructure.persistence.repositories.sqlalchemy_repositories import SqlAlchemyCaseRepository
    repo = SqlAlchemyCaseRepository(test_db_session)
    await repo.add(case)
    await test_db_session.commit()

    async def mock_get_async_session():
        yield test_db_session
    monkeypatch.setattr("src.worker.get_async_session", mock_get_async_session)

    # Act
    await run_dispatch_email_task({}, case_id, "student@test.com")

    # Assert: 10 base * 1.0 risk * 1.5 SLA = 15 points
    stmt = select(PointLedger).where(PointLedger.case_id == case_id, PointLedger.action == "send_email")
    result = await test_db_session.execute(stmt)
    entry = result.scalar_one()
    assert entry.points == 15

@pytest.mark.asyncio
async def test_run_student_booked_task_no_sla(test_db_session, setup_data, monkeypatch):
    sid, advisor_id = setup_data
    case_id = uuid4()
    
    # Case assigned 2 days ago (should NOT trigger penalty if SLA is bypassed)
    assigned_at = datetime.now(UTC) - timedelta(days=2)
    case = Case(case_id=case_id, sid=sid, assigned_advisor_id=advisor_id, assigned_at=assigned_at)
    case.intervention_status = InterventionStatus.SENT
    
    from src.infrastructure.persistence.repositories.sqlalchemy_repositories import SqlAlchemyCaseRepository
    repo = SqlAlchemyCaseRepository(test_db_session)
    await repo.add(case)
    await test_db_session.commit()

    async def mock_get_async_session():
        yield test_db_session
    monkeypatch.setattr("src.worker.get_async_session", mock_get_async_session)

    # Act
    await run_student_booked_task({}, case_id, datetime.now(UTC))

    # Assert: 50 base * 1.0 risk = 50 points (SLA bypassed by passing None)
    stmt = select(PointLedger).where(PointLedger.case_id == case_id, PointLedger.action == "student_booked")
    result = await test_db_session.execute(stmt)
    entry = result.scalar_one()
    assert entry.points == 50

@pytest.mark.asyncio
async def test_run_case_resolved_task_points(test_db_session, setup_data, monkeypatch):
    sid, advisor_id = setup_data
    case_id = uuid4()
    
    # Case assigned 18 hours ago (SLA multiplier 1.2x)
    assigned_at = datetime.now(UTC) - timedelta(hours=18)
    case = Case(case_id=case_id, sid=sid, assigned_advisor_id=advisor_id, assigned_at=assigned_at)
    case.intervention_status = InterventionStatus.SUPPORTING
    
    from src.infrastructure.persistence.repositories.sqlalchemy_repositories import SqlAlchemyCaseRepository
    repo = SqlAlchemyCaseRepository(test_db_session)
    await repo.add(case)
    await test_db_session.commit()

    async def mock_get_async_session():
        yield test_db_session
    monkeypatch.setattr("src.worker.get_async_session", mock_get_async_session)

    # Act
    from src.domain.value_objects.student_satisfaction import StudentSatisfaction
    await run_case_resolved_task({}, case_id, advisor_id, datetime.now(UTC), StudentSatisfaction.NORMAL)

    # Assert: 100 base * 1.0 risk * 1.2 SLA = 120 points
    stmt = select(PointLedger).where(PointLedger.case_id == case_id, PointLedger.action == "resolve_case")
    result = await test_db_session.execute(stmt)
    entry = result.scalar_one()
    assert entry.points == 120
