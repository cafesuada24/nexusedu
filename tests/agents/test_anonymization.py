"""Tests for late-stage anonymization and PII hardening."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.nodes.sql_worker import sql_worker_node
from src.api.models.response import JobStatusResponse
from src.api.services.alerts import AlertService
from src.baml_client.types import GeneratedSQL
from src.types import BoundedDict

if TYPE_CHECKING:
    from src.agents.state import SQLTask


def test_sql_worker_node_dynamic_masking_viewer(test_db_manager) -> None:
    """Verify sql_worker_node wraps the query with EXCLUDE for viewer role."""
    state: SQLTask = {
        'db_id': 'sis_db',
        'query_intent': 'Get student grades',
        'data': None,
        'sql': None,
        'error': None,
    }

    config = {
        'configurable': {'db_manager': test_db_manager, 'user_role': 'viewer'}
    }

    mock_sql_data = GeneratedSQL(
        sql='SELECT * FROM students',
        explanation='Testing',
        accessed_tables=['students'],
        dialect_used='duckdb',
    )

    with (
        patch(
            'src.agents.nodes.sql_worker.b.GenerateSQL', return_value=mock_sql_data
        ),
        patch.object(
            test_db_manager,
            'execute',
            return_value=[{'col': 'val'}],
        ) as mock_exec,
    ):
        result = sql_worker_node(state, config)

        mock_exec.assert_called_once()
        called_db_id, called_sql = mock_exec.call_args[0]
        assert called_db_id == 'sis_db'
        # Verify that all PII columns are in the EXCLUDE clause
        assert 'EXCLUDE' in called_sql
        assert 'student_name' in called_sql
        assert 'email' in called_sql
        assert 'phone' in called_sql
        assert 'SELECT * FROM students' in called_sql
        assert result['results'][0]['data'] == [{'col': 'val'}]


def test_sql_worker_node_no_masking_admin(test_db_manager) -> None:
    """Verify sql_worker_node does not wrap the query with EXCLUDE for admin role."""
    state: SQLTask = {
        'db_id': 'sis_db',
        'query_intent': 'Get all students',
        'data': None,
        'sql': None,
        'error': None,
    }

    config = {'configurable': {'db_manager': test_db_manager, 'user_role': 'admin'}}

    mock_sql_data = GeneratedSQL(
        sql='SELECT * FROM students',
        explanation='Testing',
        accessed_tables=['students'],
        dialect_used='duckdb',
    )

    with (
        patch(
            'src.agents.nodes.sql_worker.b.GenerateSQL', return_value=mock_sql_data
        ),
        patch.object(
            test_db_manager,
            'execute',
            return_value=[{'col': 'val'}],
        ) as mock_exec,
    ):
        result = sql_worker_node(state, config)

        mock_exec.assert_called_once()
        called_db_id, called_sql = mock_exec.call_args[0]
        assert 'EXCLUDE' not in called_sql
        assert called_sql == 'SELECT * FROM students'


@pytest.mark.anyio
async def test_email_draft_no_pii_to_ai(test_db_manager) -> None:
    """Verify that student PII is not sent directly to the AI draft generator.

    Note: In the refactored version, we use BAML directly. We verify that
    the context string sent to BAML contains performance data but not
    raw student names or emails.
    """
    sid = 'S001_SECRET'
    student_name = 'Real Name'
    email = 'real@ex.com'

    # Setup dummy student
    test_db_manager.ingest_records(
        'sis_db',
        'students',
        [
            {
                'sid': sid,
                'student_name': student_name,
                'email': email,
                'intervention_status': 'new',
            },
        ],
    )

    # Setup dummy history
    test_db_manager.ingest_records(
        'sis_db',
        'student_status_history',
        [
            {
                'history_id': '1',
                'sid': sid,
                'academic_year': '2024',
                'semester': 1,
                'baseline_avg': 85.0,
                'baseline_std': 5.0,
                'current_score_avg': 70.0,
                'z_score': -3.0,
                'anomaly_flag': 1,
            },
        ],
    )

    job_id = 'test_job'
    jobs = BoundedDict[str, JobStatusResponse](maxsize=10)
    service = AlertService(test_db_manager)

    with patch(
        'src.api.services.alerts.b_async.GenerateDraftEmail', new_callable=AsyncMock
    ) as mock_baml:
        mock_baml.return_value = 'Hello {{STUDENT_NAME}}'

        await service.run_email_draft_task(job_id, sid, jobs)

        # Check BAML was called
        mock_baml.assert_called_once()

        # Analyze the prompt context
        args, _kwargs = mock_baml.call_args
        context_sent_to_ai = args[1]  # context_str is the second arg

        # Verify performance data is there
        assert "z_score': -3.0" in context_sent_to_ai
        # Verify PII is NOT there
        assert student_name not in context_sent_to_ai
        assert email not in context_sent_to_ai
