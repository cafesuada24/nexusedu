"""Integration tests for the Agent Assistant API."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

def test_read_root() -> None:
    """Verifies that the root endpoint returns a 200 status and a welcome message."""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    assert "Welcome to the Agent Assistant API v1" in response.json()["message"]

def test_health_check() -> None:
    """Verifies that the health check endpoint returns a 200 status and indicates it's online."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "online"
    assert "timestamp" in response.json()

# Note: Testing /query would require a more complex setup with mocked LLMs/DBs
# to avoid actual API costs and external dependencies during CI.
