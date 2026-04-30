"""Integration tests for agent query routes."""

from __future__ import annotations

import pytest
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_submit_query(client: TestClient) -> None:
    """Verify that natural language queries can be submitted."""
    query = "What is the average score of students in CS?"
    
    response = client.post(f'/api/v1/query?query={query}')
    
    assert response.status_code == 202
    data = response.json()
    assert 'job_id' in data
    
@pytest.mark.asyncio
async def test_submit_query_unauthorized(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that unauthorized users cannot submit queries."""
    from src.api.auth import current_active_user, User, UserRole
    import uuid
    
    # Override with viewer who doesn't have query:execute scope
    viewer = User(
        id=uuid.uuid4(),
        email='v@ex.com',
        hashed_password='...',
        role=UserRole.VIEWER.value,
        is_active=True,
        is_verified=True
    )
    
    from src.api.main import app
    app.dependency_overrides[current_active_user] = lambda: viewer
    
    response = client.post('/api/v1/query?query=test')
    assert response.status_code == 403
    
    app.dependency_overrides.clear()
