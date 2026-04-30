"""Unit tests for the QueryService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.presentation.api.services.query import QueryService
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
    """Verify that a successful agent execution returns the correct response."""
    job_id = 'job_123'
    query = 'How many students are at risk?'
    user_dict = {'role': 'admin'}

    # Mock successful agent response with a table
    mock_agent.ainvoke.return_value = {
        'messages': [{'content': 'There are 5 students at risk.'}],
        'results': [{'data': [{'sid': 'S1', 'status': 'risk'}]}],
    }

    result = await query_service.run_agent_task(job_id, query, None, user_dict)

    assert result.answer == 'There are 5 students at risk.'
    assert len(result.tables) == 1
    assert result.tables[0][0]['sid'] == 'S1'


@pytest.mark.asyncio
async def test_run_agent_task_failure(query_service, mock_agent):
    """Verify that agent execution failure raises an exception."""
    job_id = 'job_fail'
    query = 'error query'

    mock_agent.ainvoke.side_effect = Exception('Agent crashed')

    with pytest.raises(Exception, match='Agent crashed'):
        await query_service.run_agent_task(job_id, query, None, {})


@pytest.mark.asyncio
async def test_run_agent_task_empty_state(query_service, mock_agent):
    """Verify handling of empty state returned by agent raises ValueError."""
    job_id = 'job_empty'

    mock_agent.ainvoke.return_value = None

    with pytest.raises(ValueError, match='empty or invalid state'):
        await query_service.run_agent_task(job_id, 'empty', None, {})
