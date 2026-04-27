"""Integration tests for health and basic routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

def test_read_root(client: TestClient) -> None:
    """Verifies that the root endpoint returns a 200 status and a welcome message."""
    response = client.get('/api/v1/')
    assert response.status_code == 200
    assert 'Welcome to the Agent Assistant API v1' in response.json()['message']

def test_health_check(client: TestClient) -> None:
    """Verifies that the health check endpoint returns a 200 status and indicates it's online."""
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'online'
    assert 'timestamp' in response.json()
