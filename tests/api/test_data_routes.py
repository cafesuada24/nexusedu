"""Integration tests for data ingestion routes."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from src.database.manager import DatabaseManager

def test_ingest_data_success(client: TestClient, test_db_manager: DatabaseManager) -> None:
    """Verify that the /data/ingest endpoint works correctly."""
    payload = {
        'batch_id': 'batch-123',
        'upload_timestamp': datetime.now().isoformat(),
        'data_sources': [
            {
                'source_type': 'sis',
                'records': [
                    {
                        'sid': 'API_S001',
                        'student_name': 'API Student',
                        'email': 'api@example.com',
                    },
                ],
            },
            {
                'source_type': 'lms',
                'records': [
                    {
                        'sid': 'API_S001',
                        'course_id': 'C001',
                        'course_name': 'Course 1',
                        'test_type': 'Exam',
                        'score': 85.0,
                        'timestamp': 1600000000.0,
                        'academic_year': 1,
                        'semester': 1,
                    },
                ],
            },
        ],
    }

    response = client.post('/api/v1/data/ingest', json=payload)
    assert response.status_code == 200
    assert response.json()['status'] == 'success'

    # Verify data in DB
    sis_data = test_db_manager.execute(
        'sis_db', "SELECT * FROM students WHERE sid = 'API_S001'",
    )
    assert len(sis_data) == 1

    lms_data = test_db_manager.execute(
        'lms_db', "SELECT * FROM activities WHERE sid = 'API_S001'",
    )
    assert len(lms_data) == 1

def test_ingest_custom_data(client: TestClient, test_db_manager: DatabaseManager) -> None:
    """Verify that custom data ingestion works via API."""
    payload = {
        'batch_id': 'batch-custom',
        'upload_timestamp': datetime.now().isoformat(),
        'data_sources': [
            {
                'source_type': 'custom',
                'table_name': 'api_custom_table',
                'records': [{'api_col': 'api_val'}],
            },
        ],
    }

    response = client.post('/api/v1/data/ingest', json=payload)
    assert response.status_code == 200

    # Verify dynamic table
    results = test_db_manager.execute('sis_db', 'SELECT * FROM api_custom_table')
    assert len(results) == 1
    assert results[0]['api_col'] == 'api_val'
