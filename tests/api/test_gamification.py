"""Integration tests for Gamification features."""

from __future__ import annotations

from typing import TYPE_CHECKING
import time
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from src.database.manager import DatabaseManager


def test_draft_review_points(client: TestClient, test_db_manager: DatabaseManager) -> None:
    """Verify that /alerts/{sid}/draft/review awards points."""
    sid = 'GAM_1'
    test_db_manager.ingest_records(
        'sis_db',
        'students',
        [{'sid': sid, 'student_name': 'G1', 'email': 'g1@ex.com'}],
    )

    response = client.post(f'/api/v1/alerts/{sid}/draft/review')
    assert response.status_code == 200
    assert response.json()['status'] == 'success'

    # Check ledger
    results = test_db_manager.execute(
        'sis_db', f"SELECT points, action_type FROM advisor_points_ledger WHERE sid = '{sid}'"
    )
    assert len(results) == 1
    assert results[0]['action_type'] == 'draft_reviewed'
    # Base points for draft_reviewed is 5.
    assert results[0]['points'] >= 5


def test_email_sent_points(client: TestClient, test_db_manager: DatabaseManager) -> None:
    """Verify that sending an email awards points."""
    sid = 'GAM_2'
    test_db_manager.ingest_records(
        'sis_db',
        'students',
        [{'sid': sid, 'student_name': 'G2', 'email': 'g2@ex.com'}],
    )

    response = client.post(f'/api/v1/alerts/{sid}/send', json={'body': 'test'})
    assert response.status_code == 200

    # Check ledger
    results = test_db_manager.execute(
        'sis_db', f"SELECT points, action_type FROM advisor_points_ledger WHERE sid = '{sid}'"
    )
    assert any(r['action_type'] == 'email_sent' for r in results)


def test_status_change_points(client: TestClient, test_db_manager: DatabaseManager) -> None:
    """Verify that changing status to booked/resolved awards points."""
    sid = 'GAM_3'
    test_db_manager.ingest_records(
        'sis_db',
        'students',
        [{'sid': sid, 'student_name': 'G3', 'email': 'g3@ex.com'}],
    )

    # Booked
    client.patch(f'/api/v1/alerts/{sid}/status', json={'status': 'booked'})
    # Resolved
    client.patch(f'/api/v1/alerts/{sid}/status', json={'status': 'resolved'})

    results = test_db_manager.execute(
        'sis_db', f"SELECT points, action_type FROM advisor_points_ledger WHERE sid = '{sid}'"
    )
    actions = [r['action_type'] for r in results]
    assert 'meeting_booked' in actions
    assert 'student_resolved' in actions


def test_response_time_bonus(client: TestClient, test_db_manager: DatabaseManager) -> None:
    """Verify the 1.2x multiplier for <24h response."""
    sid_fast = 'FAST_1'
    sid_slow = 'SLOW_1'
    
    test_db_manager.ingest_records(
        'sis_db',
        'students',
        [
            {'sid': sid_fast, 'student_name': 'Fast', 'email': 'f@ex.com'},
            {'sid': sid_slow, 'student_name': 'Slow', 'email': 's@ex.com'}
        ],
    )

    # Fast: alert happened 1 hour ago
    fast_time = datetime.now() - timedelta(hours=1)
    # Slow: alert happened 2 days ago
    slow_time = datetime.now() - timedelta(days=2)

    test_db_manager.execute('sis_db', f"""
        INSERT INTO student_status_history (history_id, sid, status_recorded_at) 
        VALUES ('H_FAST', '{sid_fast}', '{fast_time.isoformat()}')
    """, read_only=False)
    
    test_db_manager.execute('sis_db', f"""
        INSERT INTO student_status_history (history_id, sid, status_recorded_at) 
        VALUES ('H_SLOW', '{sid_slow}', '{slow_time.isoformat()}')
    """, read_only=False)

    # Trigger action for both
    client.post(f'/api/v1/alerts/{sid_fast}/draft/review')
    client.post(f'/api/v1/alerts/{sid_slow}/draft/review')

    res_fast = test_db_manager.execute('sis_db', f"SELECT points FROM advisor_points_ledger WHERE sid = '{sid_fast}'")[0]
    res_slow = test_db_manager.execute('sis_db', f"SELECT points FROM advisor_points_ledger WHERE sid = '{sid_slow}'")[0]

    # Base is 5. Fast should be 5 * 1.2 = 6. Slow should be 5.
    assert res_fast['points'] == 6
    assert res_slow['points'] == 5


def test_leaderboard(client: TestClient, test_db_manager: DatabaseManager) -> None:
    """Verify the leaderboard API aggregates points correctly."""
    # Seed ledger with some data
    test_db_manager.execute('sis_db', """
        INSERT INTO advisor_points_ledger (id, advisor_id, action_type, points, sid, timestamp)
        VALUES 
            ('L1', 'adv_1', 'action', 100, 's1', current_timestamp),
            ('L2', 'adv_1', 'action', 50, 's2', current_timestamp),
            ('L3', 'adv_2', 'action', 80, 's3', current_timestamp),
            ('L4', 'adv_2', 'action', 10, 's4', current_timestamp - INTERVAL '10 days')
    """, read_only=False)

    # All time
    resp = client.get('/api/v1/advisors/leaderboard?time_window=all_time')
    data = resp.json()
    # adv_1: 150, adv_2: 90
    assert data[0]['advisor_id'] == 'adv_1'
    assert data[0]['total_points'] == 150
    assert data[1]['advisor_id'] == 'adv_2'
    assert data[1]['total_points'] == 90

    # Weekly (adv_2's L4 should be excluded)
    resp = client.get('/api/v1/advisors/leaderboard?time_window=weekly')
    data = resp.json()
    # adv_1: 150, adv_2: 80
    assert data[0]['advisor_id'] == 'adv_1'
    assert data[0]['total_points'] == 150
    assert data[1]['advisor_id'] == 'adv_2'
    assert data[1]['total_points'] == 80
