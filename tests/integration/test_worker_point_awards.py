from datetime import UTC, datetime, timedelta
from uuid import uuid4

import contextlib
import pytest
from sqlalchemy import select

from src.domain.entities.case import Case
from src.domain.value_objects.status import InterventionStatus, RiskStatus
from src.infrastructure.database.models import (
    Advisor,
    InterventionEmail,
    PointLedger,
    Student,
)
from src.application.dtos.worker_payloads.email_payloads import DispatchEmailPayload
from src.application.dtos.worker_payloads.gamification_payloads import (
    CaseAcceptedPayload,
    CaseResolvedPayload,
    StudentBookedPayload,
)
from src.infrastructure.workers.tasks.email_tasks import run_dispatch_email_task
from src.infrastructure.workers.tasks.student_tasks import run_student_booked_task
from src.infrastructure.workers.tasks.case_tasks import (
    run_case_accepted_task,
    run_case_resolved_task,
)

@pytest.fixture
def mock_session_maker(test_db_session, monkeypatch):
    @contextlib.asynccontextmanager
    async def _mock_session_maker():
        yield test_db_session
    
    monkeypatch.setattr(
        "src.infrastructure.workers.framework.decorators.async_session_maker",
        _mock_session_maker
    )
    return _mock_session_maker


@pytest.fixture
async def setup_data(test_db_session, mock_user):
    sid = uuid4()
    advisor_id = uuid4()

    # 1. Create Student
    student = Student(
        sid=sid,
        student_name="Test Student",
        email="student@test.com",
        current_risk_status="Critical",
    )
    test_db_session.add(student)

    # 2. Create Advisor
    advisor = Advisor(
        advisor_id=advisor_id,
        user_id=mock_user.id,
        name="Test Advisor",
        email="advisor@test.com",
    )
    test_db_session.add(advisor)
    await test_db_session.commit()

    return sid, advisor_id

@pytest.fixture
def mock_container(test_db_session, monkeypatch):
    from src.core.container import Container
    from unittest.mock import AsyncMock
    
    # We want to use the real Container but mock specific things
    # Actually, we can just patch the Container methods in the worker tasks
    # OR we can patch the Container class itself in the framework.decorators
    pass

@pytest.mark.asyncio
async def test_run_case_accepted_task_points(test_db_session, setup_data, mock_session_maker):
    sid, advisor_id = setup_data
    case_id = uuid4()

    # Create a case created 1 hour ago
    created_at = datetime.now(UTC) - timedelta(hours=1)
    case = Case(case_id=case_id, sid=sid, created_at=created_at)
    # Using the repository to ensure it's in DB
    from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
        SqlAlchemyCaseRepository,
    )
    repo = SqlAlchemyCaseRepository(test_db_session)
    await repo.add(case)
    await test_db_session.commit()

    # Act
    occurred_at = datetime.now(UTC)
    payload = CaseAcceptedPayload(
        case_id=case_id,
        advisor_id=advisor_id,
        occurred_at=occurred_at
    )
    await run_case_accepted_task({}, payload)

    # Assert: 5 base * 1.0 risk * 1.5 SLA (<12h) = 7 points
    # NOTE: action is now 'accept_task' (enum value)
    stmt = select(PointLedger).where(PointLedger.case_id == case_id, PointLedger.action == "accept_task")
    result = await test_db_session.execute(stmt)
    entry = result.scalar_one()
    assert entry.points == 7

@pytest.mark.asyncio
async def test_run_dispatch_email_task_points(test_db_session, setup_data, mock_session_maker, monkeypatch):
    sid, advisor_id = setup_data
    case_id = uuid4()

    # Case assigned 1 hour ago
    assigned_at = datetime.now(UTC) - timedelta(hours=1)
    case = Case(case_id=case_id, sid=sid, assigned_advisor_id=advisor_id, assigned_at=assigned_at)
    case.intervention_status = InterventionStatus.ACCEPTED

    # Need an email record
    email = InterventionEmail(case_id=case_id, status="draft", subject="S", body="B")
    test_db_session.add(email)

    from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
        SqlAlchemyCaseRepository,
    )
    repo = SqlAlchemyCaseRepository(test_db_session)
    await repo.add(case)
    await test_db_session.commit()

    # Mock email sending service
    from unittest.mock import AsyncMock
    mock_email_service = AsyncMock()
    monkeypatch.setattr("src.core.container.AioSmtpEmailSender", lambda **kwargs: mock_email_service)
    # Actually simpler to patch Container.email_sending_service
    from src.core.container import Container
    monkeypatch.setattr(Container, "email_sending_service", mock_email_service)

    # Act
    payload = DispatchEmailPayload(case_id=case_id)
    await run_dispatch_email_task({}, payload)

    # Assert: 10 base * 1.0 risk * 1.5 SLA = 15 points
    stmt = select(PointLedger).where(PointLedger.case_id == case_id, PointLedger.action == "send_email")
    result = await test_db_session.execute(stmt)
    entry = result.scalar_one()
    assert entry.points == 15

@pytest.mark.asyncio
async def test_run_student_booked_task_no_sla(test_db_session, setup_data, mock_session_maker):
    sid, advisor_id = setup_data
    case_id = uuid4()

    # Case assigned 2 days ago (should NOT trigger penalty if SLA is bypassed)
    assigned_at = datetime.now(UTC) - timedelta(days=2)
    case = Case(case_id=case_id, sid=sid, assigned_advisor_id=advisor_id, assigned_at=assigned_at)
    case.intervention_status = InterventionStatus.SENT

    from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
        SqlAlchemyCaseRepository,
    )
    repo = SqlAlchemyCaseRepository(test_db_session)
    await repo.add(case)
    await test_db_session.commit()

    # Act
    payload = StudentBookedPayload(case_id=case_id, occurred_at=datetime.now(UTC))
    await run_student_booked_task({}, payload)

    # Assert: 50 base * 1.0 risk = 50 points (SLA bypassed by passing None)
    stmt = select(PointLedger).where(PointLedger.case_id == case_id, PointLedger.action == "student_book")
    result = await test_db_session.execute(stmt)
    entry = result.scalar_one()
    assert entry.points == 50

@pytest.mark.asyncio
async def test_run_case_resolved_task_points(test_db_session, setup_data, mock_session_maker):
    sid, advisor_id = setup_data
    case_id = uuid4()

    # Case assigned 18 hours ago (SLA multiplier 1.2x)
    assigned_at = datetime.now(UTC) - timedelta(hours=18)
    case = Case(case_id=case_id, sid=sid, assigned_advisor_id=advisor_id, assigned_at=assigned_at)
    case.intervention_status = InterventionStatus.SUPPORTING

    from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
        SqlAlchemyCaseRepository,
    )
    repo = SqlAlchemyCaseRepository(test_db_session)
    await repo.add(case)
    await test_db_session.commit()

    # Act
    from src.domain.value_objects.student_satisfaction import StudentSatisfaction
    payload = CaseResolvedPayload(
        case_id=case_id,
        advisor_id=advisor_id,
        occurred_at=datetime.now(UTC),
        satisfaction=StudentSatisfaction.GOOD
    )
    await run_case_resolved_task({}, payload)

    # Assert: 100 base * 1.0 risk * 1.2 SLA * 1.0 (GOOD) = 120 points
    stmt = select(PointLedger).where(PointLedger.case_id == case_id, PointLedger.action == "resolve_case")
    result = await test_db_session.execute(stmt)
    entry = result.scalar_one()
    assert entry.points == 120
