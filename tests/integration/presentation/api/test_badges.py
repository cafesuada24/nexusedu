"""Integration tests for Achievement Badges."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from src.infrastructure.database.models import AdvisorBadge, AdvisorPointsLedger, Case as OrmCase
from src.infrastructure.repositories.sqlalchemy_repositories import SqlAlchemyBadgeRepository
from src.domain.value_objects.badges import BADGE_MAP

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_advisor_badges_empty(client: TestClient) -> None:
    """Test fetching badges for an advisor with no badges."""
    advisor_id = str(uuid4())
    response = client.get(f"/api/v1/advisors/{advisor_id}/badges")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_advisor_badges_with_data(
    client: TestClient,
    test_db_session: AsyncSession,
) -> None:
    """Test fetching badges for an advisor with earned badges."""
    advisor_id = uuid4()
    badge_id = "century_club"
    
    test_db_session.add(
        AdvisorBadge(
            advisor_id=advisor_id,
            badge_id=badge_id
        )
    )
    await test_db_session.commit()
    
    response = client.get(f"/api/v1/advisors/{advisor_id}/badges")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["badge_id"] == badge_id
    assert data[0]["name"] == BADGE_MAP[badge_id].name


@pytest.mark.asyncio
async def test_badge_repository_stats_calculation(
    test_db_session: AsyncSession,
) -> None:
    """Verify that get_advisor_stats correctly calculates real metrics."""
    repo = SqlAlchemyBadgeRepository(test_db_session)
    advisor_id = uuid4()
    sid = uuid4()
    
    # 1. Create a case created 10 hours ago
    created_at = datetime.now() - timedelta(hours=10)
    test_db_session.add(
        OrmCase(
            case_id=uuid4(),
            sid=sid,
            assigned_advisor_id=advisor_id,
            created_at=created_at,
            status="open"
        )
    )
    
    # 2. Add an action (points ledger) for that sid taken NOW (response time = 10 hours)
    test_db_session.add(
        AdvisorPointsLedger(
            id=uuid4(),
            advisor_id=advisor_id,
            sid=sid,
            points=10,
            action_type="email_sent",
            timestamp=datetime.now()
        )
    )
    await test_db_session.commit()
    
    # 3. Get stats
    stats = await repo.get_advisor_stats(advisor_id)
    
    # We expect avg_response_hours to be approx 10.0
    assert stats["avg_response_hours"] > 0
    assert 9.0 < stats["avg_response_hours"] < 11.0
    # We expect 1 action and 1 fast action (since 10 < 24)
    assert stats["total_actions"] == 1
    assert stats["fast_action_count"] == 1
