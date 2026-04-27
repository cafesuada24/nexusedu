"""Integration tests for Kanban alert routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from fastapi.testclient import TestClient

    from src.database.manager import DatabaseManager

def test_get_alerts(client: TestClient, test_db_manager: DatabaseManager) -> None:
    """Verify that /alerts/ returns students with active alerts."""
    # Seed DB with one active alert student and one normal student
    test_db_manager.ingest_records(
        'sis_db',
        'students',
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
        ],
    )

    response = client.get('/api/v1/alerts/')
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['sid'] == 'ALERT_1'

def test_update_alert_status(client: TestClient, test_db_manager: DatabaseManager) -> None:
    """Verify that status updates work correctly."""
    test_db_manager.ingest_records(
        'sis_db',
        'students',
        [
            {
                'sid': 'PATCH_1',
                'student_name': 'P',
                'email': 'p@ex.com',
                'intervention_status': 'new',
            },
        ],
    )

    response = client.patch('/api/v1/alerts/PATCH_1/status', json={'status': 'booked'})
    assert response.status_code == 200
    assert response.json()['new_status'] == 'booked'

    # Verify in DB
    results = test_db_manager.execute(
        'sis_db', "SELECT intervention_status FROM students WHERE sid = 'PATCH_1'",
    )
    assert results[0]['intervention_status'] == 'booked'

def test_generate_draft(
    client: TestClient, test_db_manager: DatabaseManager, mock_agent: MagicMock,
) -> None:
    """Verify email draft generation with PII interpolation via background job."""
    test_db_manager.ingest_records(
        'sis_db',
        'students',
        [
            {
                'sid': 'DRAFT_1',
                'student_name': 'Alice PII',
                'email': 'alice@pii.com',
                'intervention_status': 'new',
            },
        ],
    )

    # 1. Trigger the draft generation
    response = client.post('/api/v1/alerts/DRAFT_1/draft')
    assert response.status_code == 202
    data = response.json()
    assert 'job_id' in data
    job_id = data['job_id']

    # 2. Poll for the job status
    poll_response = client.get(f'/api/v1/jobs/{job_id}')
    assert poll_response.status_code == 200
    poll_data = poll_response.json()
    assert poll_data['status'] == 'completed'
    
    result = poll_data['result']
    assert result['sid'] == 'DRAFT_1'
    assert result['recipient_email'] == 'alice@pii.com'
    # Check interpolation of {{STUDENT_NAME}} from conftest mock
    assert 'Alice PII' in result['body']
    assert mock_agent.ainvoke.called

def test_send_nudge_email(client: TestClient, test_db_manager: DatabaseManager) -> None:
    """Verify that sending a nudge updates the lifecycle."""
    test_db_manager.ingest_records(
        'sis_db',
        'students',
        [
            {
                'sid': 'SEND_1',
                'student_name': 'S',
                'email': 's@ex.com',
                'intervention_status': 'new',
            },
        ],
    )

    response = client.post('/api/v1/alerts/SEND_1/send', json={'body': 'Final content'})
    assert response.status_code == 200

    # Verify status moved to 'sent'
    results = test_db_manager.execute(
        'sis_db', "SELECT intervention_status FROM students WHERE sid = 'SEND_1'",
    )
    assert results[0]['intervention_status'] == 'sent'
