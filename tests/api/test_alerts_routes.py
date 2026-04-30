"""Integration tests for Kanban alert routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from src.domain.ports.repositories import StudentRepository


@pytest.mark.asyncio
async def test_get_alerts(
    client: TestClient, student_repository: StudentRepository
) -> None:
    """Verify that /alerts/ returns students with active alerts."""
    # Seed DB with one active alert student and one normal student
    await student_repository.ingest_students(
        [
            {
                'sid': 'ALERT_1',
                'student_name': 'Alerted',
                'email': 'a@ex.com',
                'intervention_status': 'new',
            },
            {
                'sid': 'NORMAL_1',
                'student_name': 'Normal',
                'email': 'n@ex.com',
                'intervention_status': 'none',
            },
        ]
    )
    await student_repository.session.commit()

    response = client.get('/api/v1/alerts/')
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['sid'] == 'ALERT_1'


@pytest.mark.asyncio
async def test_update_alert_status(
    client: TestClient,
    student_repository: StudentRepository,
) -> None:
    """Verify that status updates work correctly."""
    await student_repository.ingest_students(
        [
            {
                'sid': 'PATCH_1',
                'student_name': 'P',
                'email': 'p@ex.com',
                'intervention_status': 'new',
            },
        ]
    )
    await student_repository.session.commit()

    response = client.patch('/api/v1/alerts/PATCH_1/status', json={'status': 'booked'})
    print(response.json())
    assert response.status_code == 200
    assert response.json()['new_status'] == 'booked'

    # Verify in DB
    student = await student_repository.get_by_id('PATCH_1')
    assert student.intervention_status == 'booked'


@pytest.mark.asyncio
async def test_send_nudge_email(
    client: TestClient, student_repository: StudentRepository
) -> None:
    """Verify that sending a nudge updates the lifecycle."""
    await student_repository.ingest_students(
        [
            {
                'sid': 'SEND_1',
                'student_name': 'S',
                'email': 's@ex.com',
                'intervention_status': 'new',
            },
        ]
    )
    await student_repository.session.commit()

    response = client.post('/api/v1/alerts/SEND_1/send', json={'body': 'Final content'})
    assert response.status_code == 200

    # Verify status moved to 'sent'
    student = await student_repository.get_by_id('SEND_1')
    assert student.intervention_status == 'sent'
