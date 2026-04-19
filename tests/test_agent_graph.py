from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.agent import app
from src.agents.schemas import (
    DiscoveryRequest,
    PlannerTask,
    RouterPlan,
    SQLGeneration,
)


@pytest.fixture
def mock_llms():
    with (
        patch('src.agents.nodes.planner_llm') as mock_planner,
        patch('src.agents.nodes.sql_gen_llm') as mock_sql_gen,
    ):
        # In nodes.py, planner_llm is already the structured LLM
        # sql_gen_llm is NOT structured yet in llms.py, but nodes.py calls .with_structured_output
        mock_sql_gen_structured = MagicMock()
        mock_sql_gen.with_structured_output.return_value = mock_sql_gen_structured

        yield {
            'planner': mock_planner,
            'sql_gen': mock_sql_gen,
            'sql_gen_structured': mock_sql_gen_structured,
        }


def test_direct_answer_flow(mock_llms):
    """Test the DIRECT_ANSWER path."""
    # 1. Mock Planner: Choose DIRECT_ANSWER
    mock_llms['planner'].invoke.return_value = RouterPlan(
        path='DIRECT_ANSWER',
        direct_response_draft='Hello! How can I help you today?',
    )

    # 2. Mock SQL Gen (used as responder): Final response
    mock_llms['sql_gen'].invoke.return_value = AIMessage(
        content='Hello! I am your assistant. How can I help you today?',
    )

    initial_state = {'messages': [HumanMessage(content='Hi')]}
    final_state = app.invoke(initial_state)

    # Assertions
    assert final_state['routing_metadata']['path'] == 'DIRECT_ANSWER'
    assert 'Hello! I am your assistant' in final_state['messages'][-1].content
    assert not final_state.get('tasks')


def test_sql_execution_flow(mock_llms):
    """Test the SQL_EXECUTION path."""
    with patch('src.agents.nodes.execute_sql') as mock_execute:
        # Mock database results
        mock_execute.return_value = [{'id': 1, 'name': 'Jane Doe'}]
        
        # 1. Mock Planner: Choose SQL_EXECUTION
        mock_llms['planner'].invoke.return_value = RouterPlan(
            path='SQL_EXECUTION',
            tasks=[
                PlannerTask(
                    db_id='lms_db',
                    dialect='duckdb',
                    query_intent='Get all students',
                )
            ],
        )

        # 2. Mock SQL Gen Structured: Return SQL
        mock_llms['sql_gen_structured'].invoke.return_value = SQLGeneration(
            sql='SELECT * FROM students LIMIT 1',
            explanation='Querying students',
        )

        # 3. Mock SQL Gen (used as responder): Final response
        mock_llms['sql_gen'].invoke.return_value = AIMessage(
            content='Found 1 student: Jane Doe.',
        )

        initial_state = {'messages': [HumanMessage(content='Show me a student.')]}
        final_state = app.invoke(initial_state)

        # Assertions
        assert final_state['routing_metadata']['path'] == 'SQL_EXECUTION'
        assert len(final_state['results']) == 1
        assert 'Jane Doe' in final_state['messages'][-1].content


def test_discovery_loop_flow(mock_llms):
    """Test the DISCOVERY_REQUIRED loop."""
    # 1. Mock Planner: First call requests discovery
    mock_llms['planner'].invoke.side_effect = [
        RouterPlan(
            path='DISCOVERY_REQUIRED',
            discovery_requests=[DiscoveryRequest(tool_name='get_db_list')],
        ),
        RouterPlan(
            path='DIRECT_ANSWER',
            direct_response_draft='I found the databases.',
        ),
    ]

    # 2. Mock SQL Gen (used as responder): Final response
    mock_llms['sql_gen'].invoke.return_value = AIMessage(
        content='I have discovered lms_db and sis_db.',
    )

    initial_state = {'messages': [HumanMessage(content='What databases do we have?')]}
    final_state = app.invoke(initial_state)

    # Assertions
    assert final_state['discovery_context'] is not None
    assert 'AVAILABLE DATABASE REGISTRY' in final_state['discovery_context']
    assert 'lms_db and sis_db' in final_state['messages'][-1].content
