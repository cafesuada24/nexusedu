"""Integration tests for Gamification features."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest

from src.domain.entities.case import Case
from src.domain.value_objects.status import InterventionStatus, RiskStatus
from src.infrastructure.database.models import (
    PointLedger,
    StudentStatusHistory,
    Task,
    Case as OrmCase,
    Advisor,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.presentation.api.auth import User

    from src.domain.repositories.case_repository import CaseRepository
    from src.domain.repositories.student_repository import StudentRepository


@pytest.fixture(autouse=True)
async def seed_advisor(test_db_session: AsyncSession, mock_user: User) -> None:
    """Seed an advisor profile for the mock user."""
    test_db_session.add(
        Advisor(
            advisor_id=uuid4(),
            user_id=mock_user.id,
            name='Test Advisor',
            email=mock_user.email,
        )
    )
    await test_db_session.commit()


@pytest.mark.asyncio
async def test_draft_review_points(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that /cases/{cid}/draft/review awards 7 points for a Critical student (<12h)."""
    sid = uuid4()
    cid = uuid4()
    await student_repository.ingest_students(
        [
            {
                'sid': sid,
                'student_name': 'G1',
                'email': 'g1@ex.com',
                'current_risk_status': 'Critical',
            },
        ]
    )
    await case_repository.create_case(Case(case_id=cid, sid=sid))
    test_db_session.add(
        StudentStatusHistory(
            history_id=uuid4(),
            sid=sid,
            status_recorded_at=datetime.now(UTC),
            academic_year=2024,
            semester=1,
            week=1,
        ),
    )
    await test_db_session.commit()

    response = client.post(f'/api/v1/cases/{cid}/email/draft/review')
    assert response.status_code == 200
    assert response.json()['status'] == 'success'

    # Check ledger
    from sqlalchemy import select

    stmt = select(PointLedger, Task).join(Task, PointLedger.task_id == Task.task_id).join(OrmCase, Task.case_id == OrmCase.case_id).where(OrmCase.sid == sid)
    result = await test_db_session.execute(stmt)
    rows = result.all()

    assert len(rows) == 1
    ledger_entry, task = rows[0]
    assert task.action_type == 'review draft'
    assert ledger_entry.points == 7


@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_review_points(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that submitting the same Idempotency-Key twice does not double-award points."""
    sid = uuid4()
    cid = uuid4()
    idemp_key = str(uuid4())

    # Arrange
    await student_repository.ingest_students(
        [{'sid': sid, 'student_name': 'Idemp', 'email': 'i@ex.com'}]
    )
    await case_repository.create_case(Case(case_id=cid, sid=sid))
    await test_db_session.commit()
    headers = {'Idempotency-Key': idemp_key}

    # Act 1: First request (Should succeed and award points)
    resp1 = client.post(f'/api/v1/cases/{cid}/email/draft/review', headers=headers)
    assert resp1.status_code == 200

    # Act 2: Second request with IDENTICAL key (Should succeed but NOT award points)
    resp2 = client.post(f'/api/v1/cases/{cid}/email/draft/review', headers=headers)
    assert resp2.status_code == 200
    assert (
        'already triggered (idempotent)' in resp2.json()['message']
        or 'already awarded (idempotent)' in resp2.json()['message']
    )

    # Assert
    # Check that only ONE ledger entry was created
    from sqlalchemy import select

    stmt = select(PointLedger).join(Task, PointLedger.task_id == Task.task_id).join(OrmCase, Task.case_id == OrmCase.case_id).where(OrmCase.sid == sid)
    ledger_entries = (await test_db_session.execute(stmt)).scalars().all()
    assert len(ledger_entries) == 1


@pytest.mark.asyncio
async def test_duplicate_action_guard_prevents_double_points(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that the domain-level duplicate guard prevents double points even without Idempotency-Key."""
    sid = uuid4()
    cid = uuid4()
    await student_repository.ingest_students(
        [
            {
                'sid': sid,
                'student_name': 'DupGuard',
                'email': 'dg@ex.com',
                'current_risk_status': 'Critical',
            },
        ]
    )
    await case_repository.create_case(Case(case_id=cid, sid=sid))
    await test_db_session.commit()

    # Act: Two requests WITHOUT Idempotency-Key
    resp1 = client.post(f'/api/v1/cases/{cid}/email/draft/review')
    assert resp1.status_code == 200

    resp2 = client.post(f'/api/v1/cases/{cid}/email/draft/review')
    assert resp2.status_code == 200

    # Assert: Only ONE ledger entry should exist
    from sqlalchemy import select

    stmt = select(PointLedger).join(Task, PointLedger.task_id == Task.task_id).join(OrmCase, Task.case_id == OrmCase.case_id).where(OrmCase.sid == sid)
    ledger_entries = (await test_db_session.execute(stmt)).scalars().all()
    assert len(ledger_entries) == 1


@pytest.mark.asyncio
async def test_email_sent_points(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that sending an email awards points."""
    sid = uuid4()
    cid = uuid4()
    await student_repository.ingest_students(
        [
            {
                'sid': sid,
                'student_name': 'G2',
                'email': 'g2@ex.com',
                'current_risk_status': 'Critical',
            },
        ]
    )
    await case_repository.create_case(Case(case_id=cid, sid=sid))

    # We need a draft first for /send to work
    from src.infrastructure.database.models import InterventionEmail

    test_db_session.add(
        InterventionEmail(
            email_id=uuid4(),
            sid=sid,
            case_id=cid,
            subject='S',
            body='B',
            status='draft',
        )
    )
    await test_db_session.commit()

    key = str(uuid4())
    headers = {'Idempotency-Key': key}
    response = client.post(
        f'/api/v1/cases/{cid}/email/send',
        json={'body': 'test'},
        headers=headers,
    )
    assert response.status_code == 200

    # Check ledger
    from sqlalchemy import select

    stmt = select(PointLedger, Task).join(Task, PointLedger.task_id == Task.task_id).join(OrmCase, Task.case_id == OrmCase.case_id).where(OrmCase.sid == sid)
    result = await test_db_session.execute(stmt)
    rows = result.all()
    assert any(row.Task.action_type == 'send email' for row in rows)


@pytest.mark.asyncio
async def test_status_change_points(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify that changing status to booked/resolved awards points."""
    sid = uuid4()
    cid = uuid4()
    await student_repository.ingest_students(
        [
            {
                'sid': sid,
                'student_name': 'G3',
                'email': 'g3@ex.com',
                'current_risk_status': RiskStatus.CRITICAL.value,
            },
        ]
    )
    await case_repository.create_case(Case(case_id=cid, sid=sid))
    await test_db_session.commit()

    # Booked
    client.patch(f'/api/v1/cases/{cid}/status', json={'status': 'booked'})
    # Resolved
    client.patch(f'/api/v1/cases/{cid}/status', json={'status': 'resolved'})

    from sqlalchemy import select

    stmt = select(PointLedger, Task).join(Task, PointLedger.task_id == Task.task_id).join(OrmCase, Task.case_id == OrmCase.case_id).where(OrmCase.sid == sid)
    result = await test_db_session.execute(stmt)
    rows = result.all()

    actions = [row.Task.action_type for row in rows]
    assert 'student book' in actions
    assert 'resolve case' in actions


@pytest.mark.asyncio
async def test_response_time_bonus(
    client: TestClient,
    student_repository: StudentRepository,
    case_repository: CaseRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify tiered SLA multipliers (1.5x <12h, 1.2x <24h, 1.0x <72h, 0.8x >72h)."""
    sid_fast = uuid4()
    sid_mid = uuid4()
    sid_slow = uuid4()
    sid_penalty = uuid4()

    cid_fast = uuid4()
    cid_mid = uuid4()
    cid_slow = uuid4()
    cid_penalty = uuid4()

    await student_repository.ingest_students(
        [
            {
                'sid': sid_fast,
                'student_name': 'Fast',
                'email': 'f@ex.com',
                'current_risk_status': 'Critical',
            },
            {
                'sid': sid_mid,
                'student_name': 'Mid',
                'email': 'm@ex.com',
                'current_risk_status': 'Critical',
            },
            {
                'sid': sid_slow,
                'student_name': 'Slow',
                'email': 's@ex.com',
                'current_risk_status': 'Critical',
            },
            {
                'sid': sid_penalty,
                'student_name': 'Pen',
                'email': 'p@ex.com',
                'current_risk_status': 'Critical',
            },
        ]
    )
    await case_repository.create_case(Case(case_id=cid_fast, sid=sid_fast))
    await case_repository.create_case(Case(case_id=cid_mid, sid=sid_mid))
    await case_repository.create_case(Case(case_id=cid_slow, sid=sid_slow))
    await case_repository.create_case(Case(case_id=cid_penalty, sid=sid_penalty))

    # Use explicit UTC
    now = datetime.now(UTC)
    fast_time = now - timedelta(hours=1)
    mid_time = now - timedelta(hours=18)
    slow_time = now - timedelta(days=2)
    penalty_time = now - timedelta(days=4)

    test_db_session.add_all(
        [
            StudentStatusHistory(
                history_id=uuid4(),
                sid=sid_fast,
                status_recorded_at=fast_time,
                academic_year=2025,
                semester=2,
                week=1,
            ),
            StudentStatusHistory(
                history_id=uuid4(),
                sid=sid_mid,
                status_recorded_at=mid_time,
                academic_year=2025,
                semester=2,
                week=1,
            ),
            StudentStatusHistory(
                history_id=uuid4(),
                sid=sid_slow,
                status_recorded_at=slow_time,
                academic_year=2025,
                semester=2,
                week=1,
            ),
            StudentStatusHistory(
                history_id=uuid4(),
                sid=sid_penalty,
                status_recorded_at=penalty_time,
                academic_year=2025,
                semester=2,
                week=1,
            ),
        ]
    )
    await test_db_session.commit()

    # Trigger action for all
    client.post(f'/api/v1/cases/{cid_fast}/email/draft/review')
    client.post(f'/api/v1/cases/{cid_mid}/email/draft/review')
    client.post(f'/api/v1/cases/{cid_slow}/email/draft/review')
    client.post(f'/api/v1/cases/{cid_penalty}/email/draft/review')

    from sqlalchemy import select

    def get_stmt(sid: UUID):
        return select(PointLedger).join(Task, PointLedger.task_id == Task.task_id).join(OrmCase, Task.case_id == OrmCase.case_id).where(OrmCase.sid == sid)

    res_fast = (await test_db_session.execute(get_stmt(sid_fast))).scalar_one()
    res_mid = (await test_db_session.execute(get_stmt(sid_mid))).scalar_one()
    res_slow = (await test_db_session.execute(get_stmt(sid_slow))).scalar_one()
    res_penalty = (await test_db_session.execute(get_stmt(sid_penalty))).scalar_one()

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
    s1, s2, s3, s4 = uuid4(), uuid4(), uuid4(), uuid4()
    cid1, cid2, cid3, cid4 = uuid4(), uuid4(), uuid4(), uuid4()
    t1, t2, t3, t4 = uuid4(), uuid4(), uuid4(), uuid4()

    test_db_session.add_all([
        OrmCase(case_id=cid1, sid=s1),
        OrmCase(case_id=cid2, sid=s2),
        OrmCase(case_id=cid3, sid=s3),
        OrmCase(case_id=cid4, sid=s4),
    ])
    test_db_session.add_all([
        Task(task_id=t1, case_id=cid1, action_type='send email'),
        Task(task_id=t2, case_id=cid2, action_type='send email'),
        Task(task_id=t3, case_id=cid3, action_type='send email'),
        Task(task_id=t4, case_id=cid4, action_type='send email'),
    ])

    test_db_session.add_all(
        [
            PointLedger(
                id=uuid4(),
                advisor_id=adv1_id,
                task_id=t1,
                points=100,
                timestamp=datetime.now(),
            ),
            PointLedger(
                id=uuid4(),
                advisor_id=adv1_id,
                task_id=t2,
                points=50,
                timestamp=datetime.now(),
            ),
            PointLedger(
                id=uuid4(),
                advisor_id=adv2_id,
                task_id=t3,
                points=80,
                timestamp=datetime.now(),
            ),
            PointLedger(
                id=uuid4(),
                advisor_id=adv2_id,
                task_id=t4,
                points=10,
                timestamp=datetime.now() - timedelta(days=10),
            ),
        ]
    )
    await test_db_session.commit()

    # All time
    resp = client.get('/api/v1/advisors/leaderboard?time_window=all_time')
    assert resp.status_code == 200
    data = resp.json()
    items = data['items']
    assert data['metadata']['total_count'] >= 2
    # adv_1: 150, adv_2: 90
    assert items[0]['advisor_id'] == str(adv1_id)
    assert items[0]['total_points'] == 150
    assert 'sent_count' in items[0]
    assert 'resolved_count' in items[0]
    assert items[1]['advisor_id'] == str(adv2_id)
    assert items[1]['total_points'] == 90

    # Weekly (adv_2's L4 should be excluded)
    resp = client.get('/api/v1/advisors/leaderboard?time_window=weekly')
    assert resp.status_code == 200
    # adv_1: 150, adv_2: 80
    data = resp.json()
    items = data['items']
    assert items[0]['advisor_id'] == str(adv1_id)
    assert items[0]['total_points'] == 150
    assert items[1]['advisor_id'] == str(adv2_id)
    assert items[1]['total_points'] == 80


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
