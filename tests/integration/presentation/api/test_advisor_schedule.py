"""Integration tests for advisor schedule management API."""

import uuid
from datetime import date, time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.infrastructure.database.models import Advisor, AdvisorWorkingHours, User


@pytest.fixture
async def seeded_advisor(test_db_session: AsyncSession, mock_user: User) -> Advisor:
    """Seed an advisor profile for the mock user."""
    advisor = Advisor(
        advisor_id=uuid.uuid4(),
        user_id=mock_user.id,
        name="Schedule Advisor",
        email=mock_user.email,
    )
    test_db_session.add(advisor)
    await test_db_session.commit()
    return advisor


@pytest.mark.asyncio
async def test_get_schedule_empty(client: TestClient, seeded_advisor: Advisor):
    # Act
    response = client.get(f"/api/v1/advisors/{seeded_advisor.advisor_id}/schedule")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["working_hours"] == []
    assert data["days_off"] == []


@pytest.mark.asyncio
async def test_add_working_hours(client: TestClient, seeded_advisor: Advisor, test_db_session: AsyncSession):
    # Act
    payload = {
        "day_of_week": 0,
        "start_time": "09:00:00",
        "end_time": "17:00:00",
        "timezone": "UTC"
    }
    response = client.post(f"/api/v1/advisors/{seeded_advisor.advisor_id}/working-hours", json=payload)
    
    # Assert
    assert response.status_code == 200
    
    # Verify in DB
    stmt = select(AdvisorWorkingHours).where(AdvisorWorkingHours.advisor_id == seeded_advisor.advisor_id)
    result = await test_db_session.execute(stmt)
    wh = result.scalars().first()
    assert wh is not None
    assert wh.day_of_week == 0
    assert wh.start_time == time(9, 0)


@pytest.mark.asyncio
async def test_get_my_schedule(client: TestClient, seeded_advisor: Advisor):
    # Act: Use the /me/schedule endpoint (mock_user is authenticated by default in client)
    response = client.get("/api/v1/advisors/me/schedule")
    
    # Assert
    if response.status_code != 200:
        print(response.json())
    assert response.status_code == 200
    data = response.json()
    assert "working_hours" in data
