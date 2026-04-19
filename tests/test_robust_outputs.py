from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.agent import app
from src.agents.schemas import (
    DecisionLogEntry,
    DeterminerDecision,
    PlannerTask,
    RouterPlan,
    SQLGeneration,
)


@pytest.fixture
def mock_llms():
    with (
        patch('src.agents.nodes.planner_llm') as mock_planner,
        patch('src.agents.nodes.sql_gen_llm') as mock_sql_gen,
        patch('src.agents.nodes.determiner_llm') as mock_determiner,
    ):
        mock_sql_gen_structured = MagicMock()
        mock_determiner_structured = MagicMock()
        
        mock_sql_gen.with_structured_output.return_value = mock_sql_gen_structured
        mock_determiner.with_structured_output.return_value = mock_determiner_structured

        yield {
            'planner': mock_planner,
            'sql_gen': mock_sql_gen,
            'sql_gen_structured': mock_sql_gen_structured,
            'determiner_structured': mock_determiner_structured,
        }


def test_table_output_expectation(mock_llms):
    """Test that a query expecting data returns a table in the message."""
    
    # 1. Planner: SQL Execution
    mock_llms['planner'].invoke.return_value = RouterPlan(
        path='SQL_EXECUTION',
        tasks=[PlannerTask(db_id='lms_db', dialect='duckdb', query_intent='avg scores')]
    )

    # 2. SQL Gen: Return SQL
    mock_llms['sql_gen_structured'].invoke.return_value = SQLGeneration(
        sql='SELECT 85 as avg_score', explanation='Calculating average'
    )

    # 3. Determiner: Finish (no visualization)
    mock_llms['determiner_structured'].invoke.return_value = DeterminerDecision(
        decision=DecisionLogEntry(reasoning='Data retrieved.', next_step='finish')
    )

    # 4. Responder: Return a markdown table
    table_content = "| avg_score |\n|-----------|\n| 85        |"
    mock_llms['sql_gen'].invoke.return_value = AIMessage(
        content=f"Here is the average score:\n\n{table_content}"
    )

    initial_state = {'messages': [HumanMessage(content='What is the average score?')]}
    final_state = app.invoke(initial_state)

    # Assertions
    last_msg = final_state['messages'][-1].content
    assert '| avg_score |' in last_msg
    assert '85' in last_msg
    assert final_state.get('viz_json') is None or final_state.get('viz_json') == 'NONE'


def test_visualization_output_expectation(mock_llms):
    """Test that a query expecting a visualization returns viz_json."""
    
    # 1. Planner: SQL Execution
    mock_llms['planner'].invoke.return_value = RouterPlan(
        path='SQL_EXECUTION',
        tasks=[PlannerTask(db_id='lms_db', dialect='duckdb', query_intent='scores by student')]
    )

    # 2. SQL Gen: Return SQL
    mock_llms['sql_gen_structured'].invoke.return_value = SQLGeneration(
        sql='SELECT student_id, score FROM assessments', explanation='Getting scores'
    )

    # 3. Determiner: Visualize
    mock_llms['determiner_structured'].invoke.return_value = DeterminerDecision(
        decision=DecisionLogEntry(reasoning='Trend analysis requested.', next_step='visualize')
    )

    # 4. Mock sql_gen.invoke with side effect to handle viz_agent and responder
    def sql_gen_side_effect(messages):
        # The visualization_agent uses a specific system message
        if any("visualization expert" in str(m.content) for m in messages):
            return AIMessage(content='{"data": [{"x": [1, 2], "y": [10, 20], "type": "bar"}]}')
        # The responder uses the RESPONDER_SYSTEM_PROMPT or similar
        return AIMessage(content='I have generated a chart for student scores.')

    mock_llms['sql_gen'].invoke.side_effect = sql_gen_side_effect

    initial_state = {'messages': [HumanMessage(content='Visualize student scores.')]}
    final_state = app.invoke(initial_state)

    # Assertions
    assert final_state.get('viz_json') is not None
    assert 'bar' in final_state['viz_json']
    assert 'generated a chart' in final_state['messages'][-1].content


def test_both_table_and_visualization(mock_llms):
    """Test that a query can return both a table and a visualization."""
    
    # 1. Planner: SQL Execution
    mock_llms['planner'].invoke.return_value = RouterPlan(
        path='SQL_EXECUTION',
        tasks=[PlannerTask(db_id='lms_db', dialect='duckdb', query_intent='complex analysis')]
    )

    # 2. SQL Gen: Return SQL
    mock_llms['sql_gen_structured'].invoke.return_value = SQLGeneration(
        sql='SELECT * FROM data', explanation='Complex query'
    )

    # 3. Determiner: Visualize
    mock_llms['determiner_structured'].invoke.return_value = DeterminerDecision(
        decision=DecisionLogEntry(reasoning='Both summary and trends needed.', next_step='visualize')
    )

    # 4. Mock sql_gen.invoke with side effect
    def sql_gen_side_effect(messages):
        if any("visualization expert" in str(m.content) for m in messages):
            return AIMessage(content='{"data": "plotly_json"}')
        return AIMessage(content="Here is the table:\n| A | B |\n|---|---|\n| 1 | 2 |\n\nAnd I've created a chart.")

    mock_llms['sql_gen'].invoke.side_effect = sql_gen_side_effect

    initial_state = {'messages': [HumanMessage(content='Give me a table and a chart of the data.')]}
    final_state = app.invoke(initial_state)

    # Assertions
    assert '| A | B |' in final_state['messages'][-1].content
    assert final_state.get('viz_json') == '{"data": "plotly_json"}'
    assert "created a chart" in final_state['messages'][-1].content
