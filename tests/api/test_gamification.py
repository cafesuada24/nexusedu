"""Integration tests for Gamification features."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from src.infrastructure.database.models import AdvisorPointsLedger, StudentStatusHistory

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.domain.repositories.interfaces import AdvisorRepository, StudentRepository


@pytest.mark.asyncio
async def test_draft_review_points(
    client: TestClient,
    student_repository: StudentRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that /alerts/{sid}/draft/review awards points."""
    sid = 'GAM_1'
    await student_repository.ingest_students(
        [
            {'sid': sid, 'student_name': 'G1', 'email': 'g1@ex.com'},
        ]
    )
    await student_repository.session.commit()

    response = client.post(f'/api/v1/alerts/{sid}/draft/review')
    assert response.status_code == 200
    assert response.json()['status'] == 'success'

    # Check ledger
    from sqlalchemy import select

    stmt = select(AdvisorPointsLedger).where(AdvisorPointsLedger.sid == sid)
    result = await test_db_session.execute(stmt)
    ledger_entries = result.scalars().all()

    assert len(ledger_entries) == 1
    assert ledger_entries[0].action_type == 'draft_reviewed'
    # Base points for draft_reviewed is 5.
    assert ledger_entries[0].points >= 5


@pytest.mark.asyncio
async def test_email_sent_points(
    client: TestClient,
    student_repository: StudentRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that sending an email awards points."""
    sid = 'GAM_2'
    await student_repository.ingest_students(
        [
            {'sid': sid, 'student_name': 'G2', 'email': 'g2@ex.com'},
        ]
    )

    # We need a draft first for /send to work
    from src.infrastructure.database.models import InterventionEmail

    test_db_session.add(
        InterventionEmail(
            email_id='E1',
            sid=sid,
            subject='S',
            body='B',
            status='draft',
        )
    )
    await test_db_session.commit()

    response = client.post(f'/api/v1/alerts/{sid}/send', json={'body': 'test'})
    assert response.status_code == 200

    # Check ledger
    from sqlalchemy import select

    stmt = select(AdvisorPointsLedger).where(AdvisorPointsLedger.sid == sid)
    result = await test_db_session.execute(stmt)
    ledger_entries = result.scalars().all()
    assert any(r.action_type == 'email_sent' for r in ledger_entries)


@pytest.mark.asyncio
async def test_status_change_points(
    client: TestClient,
    student_repository: StudentRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that changing status to booked/resolved awards points."""
    sid = 'GAM_3'
    await student_repository.ingest_students(
        [
            {'sid': sid, 'student_name': 'G3', 'email': 'g3@ex.com'},
        ]
    )
    await student_repository.session.commit()

    # Booked
    client.patch(f'/api/v1/alerts/{sid}/status', json={'status': 'booked'})
    # Resolved
    client.patch(f'/api/v1/alerts/{sid}/status', json={'status': 'resolved'})

    from sqlalchemy import select

    stmt = select(AdvisorPointsLedger).where(AdvisorPointsLedger.sid == sid)
    result = await test_db_session.execute(stmt)
    ledger_entries = result.scalars().all()

    actions = [r.action_type for r in ledger_entries]
    assert 'meeting_booked' in actions
    assert 'student_resolved' in actions


@pytest.mark.asyncio
async def test_response_time_bonus(
    client: TestClient,
    student_repository: StudentRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify the 1.2x multiplier for <24h response."""
    sid_fast = 'FAST_1'
    sid_slow = 'SLOW_1'

    await student_repository.ingest_students(
        [
            {'sid': sid_fast, 'student_name': 'Fast', 'email': 'f@ex.com'},
            {'sid': sid_slow, 'student_name': 'Slow', 'email': 's@ex.com'},
        ]
    )

    # Fast: alert happened 1 hour ago
    fast_time = datetime.now() - timedelta(hours=1)
    # Slow: alert happened 2 days ago
    slow_time = datetime.now() - timedelta(days=2)

    test_db_session.add_all(
        [
            StudentStatusHistory(
                history_id='H_FAST',
                sid=sid_fast,
                status_recorded_at=fast_time,
                academic_year=2025,
                semester=2,
                week=1,
            ),
            StudentStatusHistory(
                history_id='H_SLOW',
                sid=sid_slow,
                status_recorded_at=slow_time,
                academic_year=2025,
                semester=2,
                week=1,
            ),
        ]
    )
    await test_db_session.commit()

    # Trigger action for both
    client.post(f'/api/v1/alerts/{sid_fast}/draft/review')
    client.post(f'/api/v1/alerts/{sid_slow}/draft/review')

    from sqlalchemy import select

    stmt_fast = select(AdvisorPointsLedger).where(AdvisorPointsLedger.sid == sid_fast)
    stmt_slow = select(AdvisorPointsLedger).where(AdvisorPointsLedger.sid == sid_slow)

    res_fast = (await test_db_session.execute(stmt_fast)).scalar_one()
    res_slow = (await test_db_session.execute(stmt_slow)).scalar_one()

    # Base is 5. Fast should be 5 * 1.2 = 6. Slow should be 5.
    assert res_fast.points == 6
    assert res_slow.points == 5


@pytest.mark.asyncio
async def test_leaderboard(client: TestClient, test_db_session: AsyncSession) -> None:
    """Verify the leaderboard API aggregates points correctly."""
    # Seed ledger with some data
    test_db_session.add_all(
        [
            AdvisorPointsLedger(
                id='L1',
                advisor_id='adv_1',
                action_type='action',
                points=100,
                sid='s1',
                timestamp=datetime.now(),
            ),
            AdvisorPointsLedger(
                id='L2',
                advisor_id='adv_1',
                action_type='action',
                points=50,
                sid='s2',
                timestamp=datetime.now(),
            ),
            AdvisorPointsLedger(
                id='L3',
                advisor_id='adv_2',
                action_type='action',
                points=80,
                sid='s3',
                timestamp=datetime.now(),
            ),
            AdvisorPointsLedger(
                id='L4',
                advisor_id='adv_2',
                action_type='action',
                points=10,
                sid='s4',
                timestamp=datetime.now() - timedelta(days=10),
            ),
        ]
    )
    await test_db_session.commit()

    # All time
    resp = client.get('/api/v1/advisors/leaderboard?time_window=all_time')
    assert resp.status_code == 200
    data = resp.json()
    # adv_1: 150, adv_2: 90
    assert data[0]['advisor_id'] == 'adv_1'
    assert data[0]['total_points'] == 150
    assert 'sent_count' in data[0]
    assert 'resolved_count' in data[0]
    assert data[1]['advisor_id'] == 'adv_2'
    assert data[1]['total_points'] == 90

    # Weekly (adv_2's L4 should be excluded)
    resp = client.get('/api/v1/advisors/leaderboard?time_window=weekly')
    assert resp.status_code == 200
    # adv_1: 150, adv_2: 80
    data = resp.json()
    assert data[0]['advisor_id'] == 'adv_1'
    assert data[0]['total_points'] == 150
    assert data[1]['advisor_id'] == 'adv_2'
    assert data[1]['total_points'] == 80


@pytest.mark.asyncio
async def test_engagement_metrics(
    client: TestClient, student_repository: StudentRepository
) -> None:
    """Verify the engagement metrics API aggregates by major correctly."""
    # Seed students with different majors and statuses
    await student_repository.ingest_students(
        [
            {
                'sid': 'S1',
                'student_name': 'S1',
                'email': 's1@ex.com',
                'major': 'CS',
                'intervention_status': 'sent',
            },
            {
                'sid': 'S2',
                'student_name': 'S2',
                'email': 's2@ex.com',
                'major': 'CS',
                'intervention_status': 'new',
            },
            {
                'sid': 'S3',
                'student_name': 'S3',
                'email': 's3@ex.com',
                'major': 'Math',
                'intervention_status': 'resolved',
            },
            {
                'sid': 'S4',
                'student_name': 'S4',
                'email': 's4@ex.com',
                'major': 'Math',
                'intervention_status': 'new',
            },
        ]
    )
    await student_repository.session.commit()

    resp = client.get('/api/v1/advisors/engagement')
    assert resp.status_code == 200
    data = resp.json()

    # Sort by faculty to be predictable
    data.sort(key=lambda x: x['faculty'])

    assert data[0]['faculty'] == 'CS'
    assert data[0]['sent'] == 1
    assert data[0]['drafted'] == 1

    assert data[1]['faculty'] == 'Math'
    assert data[1]['sent'] == 1
    assert data[1]['drafted'] == 1
