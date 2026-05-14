"""Integration tests for advisor dashboard metrics."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.value_objects.status import (
    EmailStatus,
    InterventionStatus,
    RiskStatus,
)
from src.infrastructure.database.models import (
    Advisor,
    Case,
    InterventionEmail,
    PointLedger,
    Student,
    User,
)


@pytest.fixture
async def seeded_advisor(test_db_session: AsyncSession, mock_user: User) -> Advisor:
    """Seed an advisor profile for the mock user."""
    advisor = Advisor(
        advisor_id=uuid.uuid4(),
        user_id=mock_user.id,
        name='Dashboard Advisor',
        email=mock_user.email,
    )
    test_db_session.add(advisor)
    await test_db_session.commit()
    return advisor


@pytest.mark.asyncio
async def test_get_advisor_dashboard_me(
    client: TestClient,
    seeded_advisor: Advisor,
    test_db_session: AsyncSession,
) -> None:
    """Verify the advisor emergency dashboard returns correct metrics."""
    advisor_id = seeded_advisor.advisor_id

    # 1. Priority Queue: 1 student (CRITICAL risk + NEW case)
    s1 = Student(
        sid=uuid.uuid4(),
        student_name='At Risk',
        email='risk@st.com',
        current_risk_status=RiskStatus.CRITICAL,
    )
    test_db_session.add(s1)
    c1 = Case(
        case_id=uuid.uuid4(),
        sid=s1.sid,
        assigned_advisor_id=advisor_id,
        intervention_status=InterventionStatus.NEW,
    )
    test_db_session.add(c1)

    # 2. Response KPI & Activation: 1 case with response and email
    s2 = Student(
        sid=uuid.uuid4(),
        student_name='Responded',
        email='resp@st.com',
        current_risk_status=RiskStatus.ELEVATED,
    )
    test_db_session.add(s2)
    created_at = datetime.now(UTC) - timedelta(hours=10)
    c2 = Case(
        case_id=uuid.uuid4(),
        sid=s2.sid,
        assigned_advisor_id=advisor_id,
        intervention_status=InterventionStatus.BOOKED,  # Activated!
        created_at=created_at,
    )
    test_db_session.add(c2)

    # First response 2 hours later
    test_db_session.add(
        PointLedger(
            id=uuid.uuid4(),
            advisor_id=advisor_id,
            case_id=c2.case_id,
            action='engage',
            points=5,
            earned_at=created_at + timedelta(hours=2),
        ),
    )
    # Email sent for this case
    test_db_session.add(
        InterventionEmail(
            email_id=uuid.uuid4(),
            case_id=c2.case_id,
            status=EmailStatus.SENT,
        ),
    )

    # 3. Recovery: 1 student who is now NORMAL
    s3 = Student(
        sid=uuid.uuid4(),
        student_name='Recovered',
        email='recov@st.com',
        current_risk_status=RiskStatus.NORMAL,
    )
    test_db_session.add(s3)
    c3 = Case(
        case_id=uuid.uuid4(),
        sid=s3.sid,
        assigned_advisor_id=advisor_id,
        intervention_status=InterventionStatus.RESOLVED,
        created_at=datetime.now(UTC) - timedelta(days=2),
        closed_at=datetime.now(UTC) - timedelta(days=1),
    )
    test_db_session.add(c3)
    # Points for resolve
    test_db_session.add(
        PointLedger(
            id=uuid.uuid4(),
            advisor_id=advisor_id,
            case_id=c3.case_id,
            action='resolve_case',
            points=50,
            earned_at=c3.closed_at,
        ),
    )
    # Email sent for this case (to make activation 1.0)
    test_db_session.add(
        InterventionEmail(
            email_id=uuid.uuid4(),
            case_id=c3.case_id,
            status=EmailStatus.SENT,
        ),
    )

    await test_db_session.commit()

    # Act
    response = client.get('/api/v1/advisors/me/dashboard')

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Priority Queue: Only c1 and c2 are active. c3 is RESOLVED.
    # c1: Student CRITICAL, status NEW -> Yes
    # c2: Student ELEVATED, status BOOKED -> Yes
    # Total = 2
    assert data['priority_queue'] == 2

    # Response KPI:
    # c2 has response at +2h.
    # c3 has PointLedger entry at closed_at (creation + 1 day = 24h).
    # c1 has no PointLedger entry.
    # Avg = (2 + 24) / 2 = 13 hours.
    assert data['response_kpi']['avg_response_hours'] == 13.0
    assert data['response_kpi']['sla_breach_count'] == 1
    assert data['response_kpi']['within_kpi_rate'] == 0.5

    # Activation Rate: 2 activated (c2, c3), 2 sent emails (c2, c3) -> 1.0
    assert data['activation'] == 1.0

    # Recovery Rate: 3 total students (s1, s2, s3), 1 normal (s3) -> 0.333
    assert pytest.approx(data['recovery']['recovery_rate'], 0.01) == 0.333

    # Impact:
    # current_xp = 5 + 50 = 55.
    assert data['impact']['current_xp'] == 55
    assert pytest.approx(data['impact']['completion_rate'], 0.01) == 0.333
