"""Integration tests for Admin Advisor Metrics."""

import uuid
from datetime import datetime, UTC, timedelta
import pytest
from fastapi.testclient import TestClient
from src.infrastructure.database.models import Advisor, Case, Student, Appointment, InterventionEmail, User
from src.presentation.api.auth import UserRole
from src.domain.value_objects.status import InterventionStatus, RiskStatus, EmailStatus, MeetingMethod, RiskReason
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_get_advisor_metrics_success(
    client: TestClient,
    test_db_session: AsyncSession,
) -> None:
    """Verify that admin can retrieve advisor performance metrics."""
    # Seed an advisor
    advisor_id = uuid.uuid4()
    advisor = Advisor(
        advisor_id=advisor_id,
        name="Test Advisor",
        email="advisor@example.com",
        faculty="Science"
    )
    test_db_session.add(advisor)
    
    # Seed a student
    student_id = uuid.uuid4()
    student = Student(
        sid=student_id,
        student_name="Test Student",
        email="student@example.com",
        current_risk_status=RiskStatus.NORMAL
    )
    test_db_session.add(student)
    
    # Seed a closed case (for resolution time)
    created_at = datetime.now(UTC) - timedelta(days=5)
    closed_at = datetime.now(UTC) - timedelta(days=1)
    case_closed = Case(
        case_id=uuid.uuid4(),
        sid=student_id,
        assigned_advisor_id=advisor_id,
        intervention_status=InterventionStatus.RESOLVED,
        created_at=created_at,
        closed_at=closed_at,
        risk_reason=RiskReason.GRADE_DROP
    )
    test_db_session.add(case_closed)
    
    # Seed an active case with interaction and appointment
    case_active_id = uuid.uuid4()
    case_active = Case(
        case_id=case_active_id,
        sid=student_id,
        assigned_advisor_id=advisor_id,
        intervention_status=InterventionStatus.ACCEPTED,
        created_at=datetime.now(UTC) - timedelta(days=2),
        first_interaction_at=datetime.now(UTC) - timedelta(days=1, hours=20), # Lead time = 4 hours
        risk_reason=RiskReason.GRADE_DROP
    )
    test_db_session.add(case_active)
    
    # Seed appointment for active case
    appointment = Appointment(
        appointment_id=uuid.uuid4(),
        case_id=case_active_id,
        appointment_time=datetime.now(UTC),
        duration_minutes=60,
        meeting_method=MeetingMethod.ONLINE
    )
    test_db_session.add(appointment)
    
    # Seed sent email for active case
    email = InterventionEmail(
        email_id=uuid.uuid4(),
        case_id=case_active_id,
        status=EmailStatus.SENT,
        sent_at=datetime.now(UTC)
    )
    test_db_session.add(email)
    
    await test_db_session.commit()
    
    # Perform request
    resp = client.get("/api/v1/admin/advisors/metrics")
    
    assert resp.status_code == 200
    data = resp.json()
    
    assert len(data["advisors"]) == 1
    row = data["advisors"][0]
    assert row["name"] == "Test Advisor"
    assert row["total_cases"] == 2
    assert row["active_cases"] == 1
    
    assert row["avg_resolution_days"] == pytest.approx(4.0)
    assert row["avg_lead_time_hours"] == pytest.approx(4.0)
    assert row["meeting_hours"] == pytest.approx(1.0)
    assert row["outreach_success_rate"] == pytest.approx(1.0)
    assert row["recovery_rate"] == pytest.approx(1.0)

@pytest.mark.asyncio
async def test_get_advisor_metrics_forbidden_for_advisor(
    client: TestClient,
    mock_user: User,
) -> None:
    """Verify that a non-admin user cannot access advisor metrics."""
    # Change role to advisor
    mock_user.role = UserRole.ADVISOR.value
    
    resp = client.get("/api/v1/admin/advisors/metrics")
    assert resp.status_code == 403
