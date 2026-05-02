"""Integration tests for Gamification features."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest

from src.domain.value_objects.status import InterventionStatus
from src.infrastructure.database.models import AdvisorPointsLedger, IdempotencyKey, StudentStatusHistory

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.domain.repositories.student_repository import StudentRepository


@pytest.mark.asyncio
async def test_draft_review_points(
    client: TestClient,
    student_repository: StudentRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that /alerts/{sid}/draft/review awards EXACTLY 5 points."""
    sid = uuid4()
    await student_repository.ingest_students(
        [
            {'sid': sid, 'student_name': 'G1', 'email': 'g1@ex.com', 'current_risk_status': 'Critical'},
        ]
    )
    test_db_session.add(
        StudentStatusHistory(
            history_id=uuid4(),
            sid=sid,
            status_recorded_at=datetime.now(UTC),
            academic_year=2024,
            semester=1,
            week=1,
        )
    )
    await test_db_session.commit()

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
    # Strict assertion: 5 base * 1.0 risk (Critical) * 1.5 bonus (<12h) = 7
    assert ledger_entries[0].points == 7


@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_review_points(
    client: TestClient,
    student_repository: StudentRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that submitting the same Idempotency-Key twice does not double-award points."""
    sid = uuid4()
    idemp_key = str(uuid4())

    # Arrange
    await student_repository.ingest_students([
        {'sid': sid, 'student_name': 'Idemp', 'email': 'i@ex.com'}
    ])
    await test_db_session.commit()
    headers = {'Idempotency-Key': idemp_key}

    # Act 1: First request (Should succeed and award points)
    resp1 = client.post(f'/api/v1/alerts/{sid}/draft/review', headers=headers)
    assert resp1.status_code == 200

    # Act 2: Second request with IDENTICAL key (Should succeed but NOT award points)
    resp2 = client.post(f'/api/v1/alerts/{sid}/draft/review', headers=headers)
    assert resp2.status_code == 200
    assert "already awarded (idempotent)" in resp2.json()['message']

    # Assert
    # Check that only ONE ledger entry was created
    from sqlalchemy import select
    stmt = select(AdvisorPointsLedger).where(AdvisorPointsLedger.sid == sid)
    ledger_entries = (await test_db_session.execute(stmt)).scalars().all()
    assert len(ledger_entries) == 1

    # Check that key was registered in the DB
    key_stmt = select(IdempotencyKey).where(IdempotencyKey.key == UUID(idemp_key))
    registered_key = (await test_db_session.execute(key_stmt)).scalar_one_or_none()
    assert registered_key is not None


@pytest.mark.asyncio
async def test_email_sent_points(
    client: TestClient,
    student_repository: StudentRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that sending an email awards points."""
    sid = uuid4()
    await student_repository.ingest_students(
        [
            {'sid': sid, 'student_name': 'G2', 'email': 'g2@ex.com'},
        ]
    )

    # We need a draft first for /send to work
    from src.infrastructure.database.models import InterventionEmail

    test_db_session.add(
        InterventionEmail(
            email_id=uuid4(),
            sid=sid,
            subject='S',
            body='B',
            status='draft',
        )
    )
    await test_db_session.commit()

    key = str(uuid4())
    headers = {'Idempotency-Key': key}
    response = client.post(f'/api/v1/alerts/{sid}/send', json={'body': 'test'}, headers=headers)
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
    sid = uuid4()
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
    """Verify the 1.2x multiplier for <24h response using UTC-safe boundaries."""
    sid_fast = uuid4()
    sid_mid = uuid4()
    sid_slow = uuid4()
    sid_penalty = uuid4()

    await student_repository.ingest_students(
        [
            {'sid': sid_fast, 'student_name': 'Fast', 'email': 'f@ex.com', 'current_risk_status': 'Critical'},
            {'sid': sid_mid, 'student_name': 'Mid', 'email': 'm@ex.com', 'current_risk_status': 'Critical'},
            {'sid': sid_slow, 'student_name': 'Slow', 'email': 's@ex.com', 'current_risk_status': 'Critical'},
            {'sid': sid_penalty, 'student_name': 'Pen', 'email': 'p@ex.com', 'current_risk_status': 'Critical'},
        ]
    )

    # Use explicit UTC to avoid CI/CD timezone drift
    now = datetime.now(UTC)
    fast_time = now - timedelta(hours=1)       # < 12h (1.5x)
    mid_time = now - timedelta(hours=18)       # < 24h (1.2x)
    slow_time = now - timedelta(days=2)        # < 72h (1.0x)
    penalty_time = now - timedelta(days=4)     # > 72h (0.8x)

    test_db_session.add_all(
        [
            StudentStatusHistory(history_id=uuid4(), sid=sid_fast, status_recorded_at=fast_time, academic_year=2025, semester=2, week=1),
            StudentStatusHistory(history_id=uuid4(), sid=sid_mid, status_recorded_at=mid_time, academic_year=2025, semester=2, week=1),
            StudentStatusHistory(history_id=uuid4(), sid=sid_slow, status_recorded_at=slow_time, academic_year=2025, semester=2, week=1),
            StudentStatusHistory(history_id=uuid4(), sid=sid_penalty, status_recorded_at=penalty_time, academic_year=2025, semester=2, week=1),
        ]
    )
    await test_db_session.commit()

    # Trigger action for all
    client.post(f'/api/v1/alerts/{sid_fast}/draft/review')
    client.post(f'/api/v1/alerts/{sid_mid}/draft/review')
    client.post(f'/api/v1/alerts/{sid_slow}/draft/review')
    client.post(f'/api/v1/alerts/{sid_penalty}/draft/review')

    from sqlalchemy import select

    stmt_fast = select(AdvisorPointsLedger).where(AdvisorPointsLedger.sid == sid_fast)
    stmt_mid = select(AdvisorPointsLedger).where(AdvisorPointsLedger.sid == sid_mid)
    stmt_slow = select(AdvisorPointsLedger).where(AdvisorPointsLedger.sid == sid_slow)
    stmt_penalty = select(AdvisorPointsLedger).where(AdvisorPointsLedger.sid == sid_penalty)

    res_fast = (await test_db_session.execute(stmt_fast)).scalar_one()
    res_mid = (await test_db_session.execute(stmt_mid)).scalar_one()
    res_slow = (await test_db_session.execute(stmt_slow)).scalar_one()
    res_penalty = (await test_db_session.execute(stmt_penalty)).scalar_one()

    # Base is 5. Fast = 5 * 1.5 = 7. Mid = 5 * 1.2 = 6. Slow = 5 * 1.0 = 5. Penalty = 5 * 0.8 = 4
    assert res_fast.points == 7
    assert res_mid.points == 6
    assert res_slow.points == 5
    assert res_penalty.points == 4


@pytest.mark.asyncio
async def test_leaderboard(client: TestClient, test_db_session: AsyncSession) -> None:
    """Verify the leaderboard API aggregates points correctly."""
    # Seed ledger with some data
    adv1_id = uuid4()
    adv2_id = uuid4()
    s1 = uuid4()
    s2 = uuid4()
    s3 = uuid4()
    s4 = uuid4()
    test_db_session.add_all(
        [
            AdvisorPointsLedger(
                id=uuid4(),
                advisor_id=adv1_id,
                action_type='action',
                points=100,
                sid=s1,
                timestamp=datetime.now(),
            ),
            AdvisorPointsLedger(
                id=uuid4(),
                advisor_id=adv1_id,
                action_type='action',
                points=50,
                sid=s2,
                timestamp=datetime.now(),
            ),
            AdvisorPointsLedger(
                id=uuid4(),
                advisor_id=adv2_id,
                action_type='action',
                points=80,
                sid=s3,
                timestamp=datetime.now(),
            ),
            AdvisorPointsLedger(
                id=uuid4(),
                advisor_id=adv2_id,
                action_type='action',
                points=10,
                sid=s4,
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
    assert data[0]['advisor_id'] == str(adv1_id)
    assert data[0]['total_points'] == 150
    assert 'sent_count' in data[0]
    assert 'resolved_count' in data[0]
    assert data[1]['advisor_id'] == str(adv2_id)
    assert data[1]['total_points'] == 90

    # Weekly (adv_2's L4 should be excluded)
    resp = client.get('/api/v1/advisors/leaderboard?time_window=weekly')
    assert resp.status_code == 200
    # adv_1: 150, adv_2: 80
    data = resp.json()
    assert data[0]['advisor_id'] == str(adv1_id)
    assert data[0]['total_points'] == 150
    assert data[1]['advisor_id'] == str(adv2_id)
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
                'sid': uuid4(),
                'student_name': 'S1',
                'email': 's1@ex.com',
                'major': 'CS',
                'intervention_status': InterventionStatus.SENT.value,
            },
            {
                'sid': uuid4(),
                'student_name': 'S2',
                'email': 's2@ex.com',
                'major': 'CS',
                'intervention_status': InterventionStatus.NOTIFIED.value,
            },
            {
                'sid': uuid4(),
                'student_name': 'S3',
                'email': 's3@ex.com',
                'major': 'Math',
                'intervention_status': InterventionStatus.RESOLVED.value,
            },
            {
                'sid': uuid4(),
                'student_name': 'S4',
                'email': 's4@ex.com',
                'major': 'Math',
                'intervention_status': InterventionStatus.NOTIFIED.value,
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
