"""Integration tests for Kanban alert routes."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from src.domain.value_objects.status import InterventionStatus

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from src.domain.repositories.student_repository import StudentRepository


@pytest.mark.asyncio
async def test_get_alerts(
    client: TestClient,
    student_repository: StudentRepository,
) -> None:
    """Verify that /api/v1/alerts returns students with active alerts."""
    await student_repository.ingest_students(
        [
            {
                'sid': (a1 := uuid.uuid4()),
                'student_name': 'Alerted',
                'email': 'a@ex.com',
                'intervention_status': InterventionStatus.NOTIFIED.value,
            },
            {
                'sid': uuid.uuid4(),
                'student_name': 'Normal',
                'email': 'n@ex.com',
                'intervention_status': InterventionStatus.NONE.value,
            },
        ]
    )
    await student_repository.session.commit()

    # Note: No trailing slash
    response = client.get('/api/v1/alerts')
    assert response.status_code == 200
    data = response.json()
    assert 'items' in data
    assert 'metadata' in data
    assert len(data['items']) == 1
    assert data['items'][0]['sid'] == str(a1)
    assert data['items'][0]['intervention_status'] == InterventionStatus.NOTIFIED.value
