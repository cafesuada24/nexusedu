"""Integration tests for data ingestion routes."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from src.infrastructure.database.models import Activity, Student

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession


def test_ingest_data_success(client: TestClient, test_db_session: AsyncSession) -> None:
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
                        'activity_id': 'ACT_001',
                        'sid': 'API_S001',
                        'course_id': 'C001',
                        'course_name': 'Course 1',
                        'test_type': 'Exam',
                        'score': 85.0,
                        'timestamp': 1600000000.0,
                        'academic_year': 2024,
                        'semester': 1,
                        'week': 1,
                    },
                ],
            },
        ],
    }

    response = client.post('/api/v1/data/ingest', json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'success'
    assert 'automatic_drafts' in data

    # Verify data in DB using the test session
    import asyncio

    async def verify() -> None:
        stmt = select(Student).where(Student.sid == 'API_S001')
        res = await test_db_session.execute(stmt)
        assert res.scalar_one_or_none() is not None

        stmt2 = select(Activity).where(Activity.sid == 'API_S001')
        res2 = await test_db_session.execute(stmt2)
        assert res2.scalar_one_or_none() is not None

    asyncio.run(verify())


def test_ingest_ignore_duplicates(
    client: TestClient, test_db_session: AsyncSession
) -> None:
    """Verify that duplicate students (by SID) are ignored during ingestion."""
    # 1. Ingest initial student
    initial_payload = {
        'batch_id': 'batch-1',
        'upload_timestamp': datetime.now().isoformat(),
        'data_sources': [
            {
                'source_type': 'sis',
                'records': [
                    {
                        'sid': 'DUP_S1',
                        'student_name': 'Original Name',
                        'email': 'original@ex.com',
                    }
                ],
            }
        ],
    }
    resp1 = client.post('/api/v1/data/ingest', json=initial_payload)
    assert resp1.status_code == 200

    # 2. Ingest same SID with different data
    duplicate_payload = {
        'batch_id': 'batch-2',
        'upload_timestamp': datetime.now().isoformat(),
        'data_sources': [
            {
                'source_type': 'sis',
                'records': [
                    {
                        'sid': 'DUP_S1',
                        'student_name': 'Duplicate Name',
                        'email': 'duplicate@ex.com',
                    }
                ],
            }
        ],
    }
    resp2 = client.post('/api/v1/data/ingest', json=duplicate_payload)
    assert resp2.status_code == 200

    # 3. Verify original data is preserved (Duplicate ignored)
    import asyncio

    async def verify() -> None:
        stmt = select(Student).where(Student.sid == 'DUP_S1')
        res = await test_db_session.execute(stmt)
        student = res.scalar_one()
        assert student.student_name == 'Original Name'
        assert student.email == 'original@ex.com'

    asyncio.run(verify())
