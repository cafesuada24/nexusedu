"""Unit tests for the QueryService."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.services.agent_metadata import AgentMetadataService
from src.presentation.api.services.query import QueryService
from src.presentation.schemas.response import QueryResponse


@pytest.fixture
def mock_agent() -> MagicMock:
    """Fixture providing a mocked LangGraph agent."""
    agent = MagicMock()
    agent.ainvoke = AsyncMock()
    return agent


@pytest.fixture
def mock_metadata_service() -> MagicMock:
    """Fixture providing a mocked AgentMetadataService."""
    return MagicMock(spec=AgentMetadataService)


@pytest.fixture
def query_service(
    mock_agent: MagicMock, mock_metadata_service: MagicMock
) -> QueryService:
    """Fixture providing a QueryService with mocked dependencies."""
    return QueryService(agent=mock_agent, metadata_service=mock_metadata_service)


@pytest.mark.asyncio
async def test_run_agent_task_success(
    query_service: QueryService,
    mock_agent: MagicMock,
) -> None:
    """Verify that a successful agent execution returns the correct response."""
    # Arrange
    job_id = 'job-123'
    test_query = 'How many students are at risk?'
    user_context = {'role': 'admin'}
    expected_answer = 'There are 5 students at risk.'
    mock_data = [{'sid': 'S1', 'status': 'risk'}]

    mock_agent.ainvoke.return_value = {
        'messages': [{'content': expected_answer}],
        'results': [{'data': mock_data}],
    }

    # Act
    result = await query_service.run_agent_task(job_id, test_query, None, user_context)

    # Assert
    assert isinstance(result, QueryResponse)
    assert result.answer == expected_answer
    assert result.tables is not None
    assert len(result.tables) == 1
    assert result.tables[0] == mock_data


@pytest.mark.asyncio
async def test_run_agent_task_failure(
    query_service: QueryService, mock_agent: MagicMock
) -> None:
    """Verify that agent execution failure raises an exception."""
    # Arrange
    job_id = 'job-fail'
    test_query = 'trigger error'
    error_message = 'Agent crashed'
    mock_agent.ainvoke.side_effect = Exception(error_message)

    # Act & Assert
    with pytest.raises(Exception, match=error_message):
        await query_service.run_agent_task(job_id, test_query, None, {})


@pytest.mark.asyncio
async def test_run_agent_task_empty_state(
    query_service: QueryService, mock_agent: MagicMock
) -> None:
    """Verify handling of empty state returned by agent raises ValueError."""
    # Arrange
    job_id = 'job-empty'
    test_query = 'empty-response'
    mock_agent.ainvoke.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match='empty or invalid state'):
        await query_service.run_agent_task(job_id, test_query, None, {})
