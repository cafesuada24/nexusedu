"""Integration tests for Metrics features."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from src.database.manager import DatabaseManager

def test_kpi_stats(client: TestClient, test_db_manager: DatabaseManager) -> None:
    """Verify the KPI stats API returns correct aggregations."""
    # Seed students
    test_db_manager.ingest_records(
        'sis_db',
        'students',
        [
            {'sid': 'S1', 'student_name': 'S1', 'email': 's1@ex.com', 'current_risk_status': 'Normal', 'intervention_status': 'none'},
            {'sid': 'S2', 'student_name': 'S2', 'email': 's2@ex.com', 'current_risk_status': 'Significant Drop', 'intervention_status': 'sent'},
        ],
    )

    resp = client.get('/api/v1/metrics/stats')
    assert resp.status_code == 200
    data = resp.json()
    
    assert data['retention_rate'] == 50.0
    assert data['dropout_rate'] == 50.0
    assert data['total_interventions'] == 1
    assert data['total_students'] == 2

def test_retention_trend(client: TestClient, test_db_manager: DatabaseManager) -> None:
    """Verify the retention trend API returns data points."""
    # Seed history
    test_db_manager.execute('sis_db', """
        INSERT INTO student_status_history (history_id, sid, academic_year, semester, week, anomaly_flag)
        VALUES
            ('H1', 'S1', 2025, 2, 1, 'normal'),
            ('H2', 'S2', 2025, 2, 1, 'anomaly')
    """, read_only=False)

    resp = client.get('/api/v1/metrics/retention')
    assert resp.status_code == 200
    data = resp.json()
    
    assert len(data) > 0
    assert data[-1]['month'] == 'W1'
    assert data[-1]['current'] == 50.0
