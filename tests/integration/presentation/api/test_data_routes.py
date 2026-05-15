"""Integration tests for data ingestion routes."""

from __future__ import annotations

import pickle
import contextlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from src.infrastructure.database.models import Activity, OutboxEvent, Student
from src.infrastructure.workers.tasks.data_tasks import run_data_ingest_task

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_session_maker(test_db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock the session maker to use the test database session."""
    @contextlib.asynccontextmanager
    async def _mock_session_maker():
        yield test_db_session
    
    monkeypatch.setattr(
        'src.infrastructure.workers.framework.decorators.async_session_maker',
        _mock_session_maker
    )


async def test_ingest_data_success(
    client: TestClient, 
    test_db_session: AsyncSession,
    mock_session_maker: None,
) -> None:
    """Verify that the /data/ingest endpoint enqueues a background job."""

    payload = {
        'batch_id': str(uuid4()),
        'upload_timestamp': datetime.now(UTC).isoformat(),
        'data_sources': [
            {
                'source_type': 'sis',
                'records': [
                    {
                        'sid': str(s1 := uuid4()),
                        'student_name': 'API Student',
                        'email': 'api@example.com',
                    },
                ],
            },
            {
                'source_type': 'lms',
                'records': [
                    {
                        'activity_id': str(a1 := uuid4()),
                        'sid': str(s1),
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
    assert 'job_id' in data

    # Verify outbox event in DB
    stmt = select(OutboxEvent).where(OutboxEvent.task_name == 'run_data_ingest_task')
    res = await test_db_session.execute(stmt)
    event = res.scalar_one()
    assert event is not None

    # Manually run the task to verify the full flow
    # The task expects (arq_ctx, payload) because of the decorator
    payload_obj = pickle.loads(event.payload)['payload']
    
    arq_ctx = {'redis': MagicMock()} # arq_ctx.get('redis') is used in decorator
    
    await run_data_ingest_task(arq_ctx, payload=payload_obj)
    await test_db_session.commit()

    # Verify data in DB
    stmt = select(Student).where(Student.sid == s1)
    res = await test_db_session.execute(stmt)
    assert res.scalar_one_or_none() is not None

    stmt2 = select(Activity).where(Activity.activity_id == a1)
    res2 = await test_db_session.execute(stmt2)
    assert res2.scalar_one_or_none() is not None


async def test_ingest_upsert_behavior(
    client: TestClient,
    test_db_session: AsyncSession,
    mock_session_maker: None,
) -> None:
    """Verify that duplicate students (by SID) are updated (upsert) during ingestion."""
    # 1. Ingest initial student
    initial_payload = {
        'batch_id': str(uuid4()),
        'upload_timestamp': datetime.now().isoformat(),
        'data_sources': [
            {
                'source_type': 'sis',
                'records': [
                    {
                        'sid': str(s1 := uuid4()),
                        'student_name': 'Original Name',
                        'email': 'original@ex.com',
                    },
                ],
            },
        ],
    }
    resp1 = client.post('/api/v1/data/ingest', json=initial_payload)
    assert resp1.status_code == 200

    # Process first task
    stmt = select(OutboxEvent).where(OutboxEvent.task_name == 'run_data_ingest_task')
    res = await test_db_session.execute(stmt)
    event = res.scalar_one()
    payload_obj = pickle.loads(event.payload)['payload']
    
    arq_ctx = {'redis': MagicMock()}
    await run_data_ingest_task(arq_ctx, payload=payload_obj)
    await test_db_session.commit()
    await test_db_session.delete(event) # Clean up for next check
    await test_db_session.commit()

    # 2. Ingest same SID with different data
    duplicate_payload = {
        'batch_id': str(uuid4()),
        'upload_timestamp': datetime.now().isoformat(),
        'data_sources': [
            {
                'source_type': 'sis',
                'records': [
                    {
                        'sid': str(s1),
                        'student_name': 'Updated Name',
                        'email': 'updated@ex.com',
                    },
                ],
            },
        ],
    }
    resp2 = client.post('/api/v1/data/ingest', json=duplicate_payload)
    assert resp2.status_code == 200

    # Process second task
    stmt = select(OutboxEvent).where(OutboxEvent.task_name == 'run_data_ingest_task')
    res = await test_db_session.execute(stmt)
    event = res.scalar_one()
    payload_obj = pickle.loads(event.payload)['payload']
    await run_data_ingest_task(arq_ctx, payload=payload_obj)
    await test_db_session.commit()

    # 3. Verify data is updated (Upsert)
    stmt = select(Student).where(Student.sid == s1)
    res = await test_db_session.execute(stmt)
    student = res.scalar_one()
    assert student.student_name == 'Updated Name'
    assert student.email == 'updated@ex.com'
