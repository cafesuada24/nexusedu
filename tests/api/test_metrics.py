"""Integration tests for Metrics features."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from src.domain.repositories.interfaces import StatusHistoryRepository, StudentRepository


@pytest.mark.asyncio
async def test_kpi_stats(
    client: TestClient, student_repository: StudentRepository
) -> None:
    """Verify the KPI stats API returns correct aggregations."""
    # Seed students
    await student_repository.ingest_students(
        [
            {
                'sid': 'S1',
                'student_name': 'S1',
                'email': 's1@ex.com',
                'current_risk_status': 'Normal',
                'intervention_status': 'none',
            },
            {
                'sid': 'S2',
                'student_name': 'S2',
                'email': 's2@ex.com',
                'current_risk_status': 'Significant Drop',
                'intervention_status': 'sent',
            },
        ]
    )

    resp = client.get('/api/v1/metrics/stats')
    assert resp.status_code == 200
    data = resp.json()

    assert data['retention_rate'] == 50.0
    assert data['dropout_rate'] == 50.0
    assert data['total_interventions'] == 1
    assert data['total_students'] == 2


@pytest.mark.asyncio
async def test_retention_trend(
    client: TestClient,
    student_repository: StudentRepository,
    status_history_repository: StatusHistoryRepository,
) -> None:
    """Verify the retention trend API returns data points."""
    # Seed students first (foreign key constraint)
    await student_repository.ingest_students(
        [
            {'sid': 'S1', 'student_name': 'S1', 'email': 's1@ex.com'},
            {'sid': 'S2', 'student_name': 'S2', 'email': 's2@ex.com'},
        ]
    )

    # Seed history
    await status_history_repository.batch_create_history(
        [
            {
                'history_id': 'H1',
                'sid': 'S1',
                'academic_year': 2025,
                'semester': 2,
                'week': 1,
                'anomaly_flag': 'Normal',
            },
            {
                'history_id': 'H2',
                'sid': 'S2',
                'academic_year': 2025,
                'semester': 2,
                'week': 1,
                'anomaly_flag': 'anomaly',
            },
        ]
    )

    resp = client.get('/api/v1/metrics/retention')
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) > 0
    assert data[-1]['month'] == 'W1'
    assert data[-1]['current'] == 50.0
