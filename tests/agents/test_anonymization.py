"""Tests for late-stage anonymization and PII hardening."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from src.agents.nodes.sql_worker import sql_worker
from src.agents.state import SQLTask
from src.api.routes.alerts import _run_email_draft_task
from src.baml_client.types import GeneratedSQL


def test_sql_worker_dynamic_masking_advisor_read(test_db_manager) -> None:
    """Verify sql_worker wraps the query with EXCLUDE for advisor:read role."""
    state: SQLTask = {
        'db_id': 'sis_db',
        'query_intent': 'Get student grades',
        'data': None,
        'sql': None,
        'error': None
    }
    
    config = {
        'configurable': {
            'db_manager': test_db_manager,
            'user_role': 'advisor:read'
        }
    }

    mock_sql_data = GeneratedSQL(
        sql="SELECT * FROM students",
        explanation="Testing",
        accessed_tables=["students"],
        dialect_used="duckdb"
    )

    with patch('src.agents.nodes.sql_worker.b.GenerateSQL', return_value=mock_sql_data):
        with patch.object(test_db_manager, 'execute', return_value=[{"col": "val"}]) as mock_exec:
            result = sql_worker(state, config)
            
            mock_exec.assert_called_once()
            called_db_id, called_sql = mock_exec.call_args[0]
            assert called_db_id == 'sis_db'
            assert 'EXCLUDE (student_name, email, phone)' in called_sql
            assert 'SELECT * FROM students' in called_sql
            assert result['results'][0]['data'] == [{"col": "val"}]


def test_sql_worker_no_masking_admin_all(test_db_manager) -> None:
    """Verify sql_worker does not wrap the query with EXCLUDE for admin:all role."""
    state: SQLTask = {
        'db_id': 'sis_db',
        'query_intent': 'Get all students',
        'data': None,
        'sql': None,
        'error': None
    }
    
    config = {
        'configurable': {
            'db_manager': test_db_manager,
            'user_role': 'admin:all'
        }
    }

    mock_sql_data = GeneratedSQL(
        sql="SELECT * FROM students",
        explanation="Testing",
        accessed_tables=["students"],
        dialect_used="duckdb"
    )

    with patch('src.agents.nodes.sql_worker.b.GenerateSQL', return_value=mock_sql_data):
        with patch.object(test_db_manager, 'execute', return_value=[{"col": "val"}]) as mock_exec:
            result = sql_worker(state, config)
            
            mock_exec.assert_called_once()
            called_db_id, called_sql = mock_exec.call_args[0]
            assert 'EXCLUDE' not in called_sql
            assert called_sql == 'SELECT * FROM students'


@pytest.mark.anyio
async def test_email_draft_anonymization(test_db_manager, mock_agent) -> None:
    """Verify PII is stripped and anonymized_id is passed to the LLM agent."""
    sid = "S001_SECRET"
    student_name = "Real Name"
    email = "real@ex.com"

    # Setup dummy student
    test_db_manager.ingest_records('sis_db', 'students', [{
        'sid': sid,
        'student_name': student_name,
        'email': email,
        'intervention_status': 'new'
    }])

    # Setup dummy history
    test_db_manager.ingest_records('sis_db', 'student_status_history', [{
        'history_id': '1',
        'sid': sid,
        'academic_year': '2024',
        'semester': 1,
        'baseline_avg': 85.0,
        'baseline_std': 5.0,
        'current_score_avg': 70.0,
        'z_score': -3.0,
        'anomaly_flag': 1
    }])

    # Use a dummy user object
    user_mock = MagicMock()
    user_mock.role = "advisor:write"

    job_id = "test_job"
    
    # Run the background task directly
    await _run_email_draft_task(job_id, sid, mock_agent, test_db_manager, user_mock)
    
    # Check agent was called
    mock_agent.ainvoke.assert_called_once()
    
    # Analyze the prompt
    args, kwargs = mock_agent.ainvoke.call_args
    query_sent_to_agent = args[0]['messages'][0]['content']
    
    assert "anonymized_id 'STU_" in query_sent_to_agent
    assert sid not in query_sent_to_agent
    assert student_name not in query_sent_to_agent
    assert email not in query_sent_to_agent
    assert "z_score': -3.0" in query_sent_to_agent
