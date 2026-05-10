"""Unit tests for the AgentCommandHandler."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.commands.agent_commands import AgentCommandHandler
from src.application.dtos.agent_dtos import AgentResponseDTO, RunAgentTaskCommand
from src.application.services.agent_metadata import AgentMetadataService


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
def mock_idempotency_repo() -> MagicMock:
    """Fixture providing a mock for the IdempotencyRepository."""
    return MagicMock()


@pytest.fixture
def agent_command_handler(
    mock_agent: MagicMock,
    mock_metadata_service: MagicMock,
    mock_idempotency_repo: MagicMock,
) -> AgentCommandHandler:
    """Fixture providing an AgentCommandHandler with mocked dependencies."""
    return AgentCommandHandler(
        agent=mock_agent,
        metadata_service=mock_metadata_service,
        idempotency_repo=mock_idempotency_repo,
    )


@pytest.mark.asyncio
async def test_handle_run_agent_task_success(
    agent_command_handler: AgentCommandHandler,
    mock_agent: MagicMock,
) -> None:
    """Verify that a successful agent execution returns the correct response DTO."""
    # Arrange
    command = RunAgentTaskCommand(
        job_id=uuid4(),
        query='How many students are at risk?',
        thread_id=None,
        user_dict={'role': 'admin'},
    )
    expected_answer = 'There are 5 students at risk.'
    mock_data = [{'sid': str(uuid4()), 'status': 'risk'}]

    mock_agent.ainvoke.return_value = {
        'messages': [{'content': expected_answer}],
        'results': [{'data': mock_data}],
    }

    # Act
    result = await agent_command_handler.handle_run_agent_task(command)

    # Assert
    assert isinstance(result, AgentResponseDTO)
    assert result.answer == expected_answer
    assert result.tables is not None
    assert len(result.tables) == 1
    assert result.tables[0] == mock_data


@pytest.mark.asyncio
async def test_handle_run_agent_task_failure(
    agent_command_handler: AgentCommandHandler, mock_agent: MagicMock,
) -> None:
    """Verify that agent execution failure raises an exception."""
    # Arrange
    command = RunAgentTaskCommand(
        job_id=uuid4(),
        query='trigger error',
        thread_id=None,
        user_dict={},
    )
    error_message = 'Agent crashed'
    mock_agent.ainvoke.side_effect = Exception(error_message)

    # Act & Assert
    with pytest.raises(Exception, match=error_message):
        await agent_command_handler.handle_run_agent_task(command)


@pytest.mark.asyncio
async def test_handle_run_agent_task_empty_state(
    agent_command_handler: AgentCommandHandler, mock_agent: MagicMock,
) -> None:
    """Verify handling of empty state returned by agent raises ValueError."""
    # Arrange
    command = RunAgentTaskCommand(
        job_id=uuid4(),
        query='empty-response',
        thread_id=None,
        user_dict={},
    )
    mock_agent.ainvoke.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match='empty or invalid state'):
        await agent_command_handler.handle_run_agent_task(command)
