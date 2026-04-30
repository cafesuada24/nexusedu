"""Unit tests for the QueryService."""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from src.presentation.api.services.query import QueryService
from src.presentation.schemas.response import JobStatusResponse
from src.domain.services.agent_metadata import AgentMetadataService

@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.ainvoke = AsyncMock()
    return agent

@pytest.fixture
def mock_metadata_service():
    return MagicMock(spec=AgentMetadataService)

@pytest.fixture
def query_service(mock_agent, mock_metadata_service):
    return QueryService(agent=mock_agent, metadata_service=mock_metadata_service)

@pytest.mark.asyncio
async def test_run_agent_task_success(query_service, mock_agent):
    """Verify that a successful agent execution updates the job store correctly."""
    job_id = "job_123"
    query = "How many students are at risk?"
    jobs = {}
    user_dict = {"role": "admin"}
    
    # Mock successful agent response with a table
    mock_agent.ainvoke.return_value = {
        "messages": [{"content": "There are 5 students at risk."}],
        "results": [
            {"data": [{"sid": "S1", "status": "risk"}]}
        ]
    }

    await query_service.run_agent_task(job_id, query, None, user_dict, jobs)
    
    assert job_id in jobs
    assert jobs[job_id].status == "completed"
    assert jobs[job_id].result.answer == "There are 5 students at risk."
    assert len(jobs[job_id].result.tables) == 1
    assert jobs[job_id].result.tables[0][0]["sid"] == "S1"

@pytest.mark.asyncio
async def test_run_agent_task_failure(query_service, mock_agent):
    """Verify that agent execution failure is captured in the job store."""
    job_id = "job_fail"
    query = "error query"
    jobs = {}
    
    mock_agent.ainvoke.side_effect = Exception("Agent crashed")

    await query_service.run_agent_task(job_id, query, None, {}, jobs)
    
    assert job_id in jobs
    assert jobs[job_id].status == "failed"
    assert "Agent crashed" in jobs[job_id].error

@pytest.mark.asyncio
async def test_run_agent_task_empty_state(query_service, mock_agent):
    """Verify handling of empty state returned by agent."""
    job_id = "job_empty"
    jobs = {}
    
    mock_agent.ainvoke.return_value = None

    await query_service.run_agent_task(job_id, "empty", None, {}, jobs)
    
    assert jobs[job_id].status == "failed"
    assert "empty or invalid state" in jobs[job_id].error
