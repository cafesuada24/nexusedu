"""Unit tests for Agent nodes."""

import pytest
from unittest.mock import MagicMock, patch
from src.agents.nodes.planner import planner_node
from src.agents.nodes.responder import responder_node
from src.agents.nodes.routing import route_planner, route_after_sql
from src.baml_client.types import NextStepPlan

@pytest.fixture
def mock_config():
    return {'configurable': {'thread_id': 'test'}}

def test_planner_node_direct_response(mock_baml, mock_config):
    """Verify planner correctly identifies a direct response path."""
    state = {'messages': [{'role': 'user', 'content': 'Hello'}]}
    
    mock_plan = MagicMock(spec=NextStepPlan)
    mock_plan.path = 'RESPOND'
    mock_plan.direct_response_draft = "Hi there!"
    mock_plan.tasks = []
    mock_plan.discovery_requests = []
    mock_plan.next_action_after_sql = None
    
    mock_baml.PlanNextStep.return_value = mock_plan
    
    result = planner_node(state, mock_config)
    
    assert result['routing_metadata']['path'] == 'RESPOND'
    assert result['routing_metadata']['direct_response_draft'] == "Hi there!"
    assert result['tasks'] == []

def test_planner_node_sql_execution(mock_baml, mock_config):
    """Verify planner correctly identifies SQL execution path."""
    state = {'messages': [{'role': 'user', 'content': 'Query students'}]}
    
    task = MagicMock()
    task.model_dump.return_value = {'db_id': 'sis_db', 'query_intent': 'get students'}
    
    mock_plan = MagicMock(spec=NextStepPlan)
    mock_plan.path = 'SQL_EXECUTION'
    mock_plan.tasks = [task]
    mock_plan.discovery_requests = []
    mock_plan.direct_response_draft = None
    mock_plan.next_action_after_sql = 'RESPOND'
    
    mock_baml.PlanNextStep.return_value = mock_plan
    
    result = planner_node(state, mock_config)
    
    assert result['routing_metadata']['path'] == 'SQL_EXECUTION'
    assert len(result['tasks']) == 1
    assert result['tasks'][0]['db_id'] == 'sis_db'

@pytest.mark.asyncio
async def test_responder_node(mock_baml, mock_config):
    """Verify responder node synthesizes the final answer."""
    state = {
        'messages': [{'role': 'user', 'content': 'test'}],
        'results': [{'db': 'sis_db', 'data': [{'count': 10}]}],
        'routing_metadata': {'direct_response_draft': None}
    }
    
    mock_baml.Respond.return_value = "Final synthesized answer"
    
    result = await responder_node(state, mock_config)
    
    assert result['messages'][-1]['role'] == 'assistant'
    assert result['messages'][-1]['content'] == "Final synthesized answer"

def test_route_planner():
    """Verify routing logic from planner."""
    # 1. To Responder
    state = {'routing_metadata': {'path': 'RESPOND'}}
    assert route_planner(state) == 'responder'
    
    # 2. To SQL
    state = {'routing_metadata': {'path': 'SQL_EXECUTION'}}
    assert route_planner(state) == 'sql_worker'
    
    # 3. To Discovery
    state = {'routing_metadata': {'path': 'DISCOVERY'}}
    assert route_planner(state) == 'discovery'

def test_route_after_sql():
    """Verify routing logic after SQL execution."""
    # 1. To Email
    state = {'routing_metadata': {'next_action_after_sql': 'EMAIL_DRAFT'}}
    assert route_after_sql(state) == 'email_agent'
    
    # 2. To Responder
    state = {'routing_metadata': {'next_action_after_sql': 'RESPOND'}}
    assert route_after_sql(state) == 'responder'
