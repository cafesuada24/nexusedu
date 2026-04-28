"""Integration tests for background query and job polling routes."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unittest.mock import MagicMock
    from fastapi.testclient import TestClient

def test_query_background_task(client: TestClient, mock_agent: MagicMock) -> None:
    """Verify that /query returns a job_id and eventually completes."""
    query_payload = {"query": "Tell me about student performance."}
    
    # 1. Trigger the query
    response = client.post("/api/v1/query", json=query_payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"
    
    job_id = data["job_id"]
    
    # 2. Poll for the job status
    # Since it's a TestClient and background tasks run synchronously in TestClient,
    # it should be completed immediately.
    poll_response = client.get(f"/api/v1/jobs/{job_id}")
    assert poll_response.status_code == 200
    poll_data = poll_response.json()
    assert poll_data["job_id"] == job_id
    assert poll_data["status"] == "completed"
    assert "result" in poll_data
    assert poll_data["result"]["answer"] == "Hello {{STUDENT_NAME}}, this is an AI draft."

def test_query_job_not_found(client: TestClient) -> None:
    """Verify that polling for a non-existent job returns 404."""
    response = client.get("/api/v1/jobs/non-existent-job-id")
    assert response.status_code == 404
