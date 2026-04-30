"""Integration tests for Kanban alert routes."""

from __future__ import annotations

import uuid
import pytest
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from src.domain.repositories.interfaces import StudentRepository, EmailRepository


@pytest.mark.asyncio
async def test_get_alerts(
    client: TestClient, student_repository: StudentRepository
) -> None:
    """Verify that /alerts/ returns students with active alerts."""
    await student_repository.ingest_students(
        [
            {
                'sid': 'A1',
                'student_name': 'Alerted',
                'email': 'a@ex.com',
                'intervention_status': 'new',
            },
            {
                'sid': 'N1',
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
    assert data[0]['sid'] == 'A1'


@pytest.mark.asyncio
async def test_update_alert_status(
    client: TestClient, student_repository: StudentRepository
) -> None:
    """Verify that status updates work correctly."""
    await student_repository.ingest_students(
        [
            {
                'sid': 'P1',
                'student_name': 'P',
                'email': 'p@ex.com',
                'intervention_status': 'new',
            },
        ]
    )
    await student_repository.session.commit()

    response = client.patch('/api/v1/alerts/P1/status', json={'status': 'booked'})
    assert response.status_code == 200

    student = await student_repository.get_by_id('P1')
    assert student.intervention_status == 'booked'


@pytest.mark.asyncio
async def test_trigger_draft(
    client: TestClient, student_repository: StudentRepository
) -> None:
    """Verify manual draft triggering."""
    await student_repository.ingest_students(
        [
            {
                'sid': 'T1',
                'student_name': 'T',
                'email': 't@ex.com',
                'intervention_status': 'new',
            },
        ]
    )
    await student_repository.session.commit()

    response = client.post('/api/v1/alerts/T1/draft/trigger')
    assert response.status_code == 202
    assert 'job_id' in response.json()


@pytest.mark.asyncio
async def test_review_draft_idempotency(
    client: TestClient,
    student_repository: StudentRepository,
) -> None:
    """Verify points awarding and idempotency for draft review."""
    sid = 'R1'
    await student_repository.ingest_students(
        [{'sid': sid, 'student_name': 'R', 'email': 'r@ex.com'}]
    )
    await student_repository.session.commit()

    key = str(uuid.uuid4())
    headers = {'Idempotency-Key': key}

    # 1. First review
    resp1 = client.post(f'/api/v1/alerts/{sid}/draft/review', headers=headers)
    print(resp1.json())
    assert resp1.status_code == 200
    assert 'awarded' in resp1.json()['message']

    # 2. Second review with same key
    resp2 = client.post(f'/api/v1/alerts/{sid}/draft/review', headers=headers)
    assert resp2.status_code == 200
    assert 'idempotent' in resp2.json()['message']


@pytest.mark.asyncio
async def test_send_email_flow(
    client: TestClient,
    student_repository: StudentRepository,
    email_repository: EmailRepository,
) -> None:
    """Verify the full email sending flow."""
    sid = 'S1'
    await student_repository.ingest_students(
        [
            {
                'sid': sid,
                'student_name': 'S',
                'email': 's@ex.com',
                'intervention_status': 'new',
            }
        ]
    )
    await email_repository.create_draft(sid, 'ADV1', 'Subject', 'Body')
    await student_repository.session.commit()

    response = client.post(f'/api/v1/alerts/{sid}/send', json={'body': 'Sent body'})
    assert response.status_code == 200

    # Check status
    student = await student_repository.get_by_id(sid)
    assert student.intervention_status == 'sent'

    # Check history
    history = client.get(f'/api/v1/alerts/{sid}/history')
    assert len(history.json()) == 1
    assert history.json()[0]['status'] == 'sent'


@pytest.mark.asyncio
async def test_get_email_draft(
    client: TestClient,
    student_repository: StudentRepository,
    email_repository: EmailRepository,
) -> None:
    """Verify retrieving the current draft content."""
    sid = 'D1'
    await student_repository.ingest_students(
        [{'sid': sid, 'student_name': 'D', 'email': 'd@ex.com'}]
    )
    await email_repository.create_draft(sid, 'ADV1', 'Draft Sub', 'Draft Body')
    await student_repository.session.commit()

    response = client.get(f'/api/v1/alerts/{sid}/draft')
    assert response.status_code == 200
    data = response.json()
    assert data['subject'] == 'Draft Sub'
    assert data['body'] == 'Draft Body'
    assert data['is_generating'] is False
