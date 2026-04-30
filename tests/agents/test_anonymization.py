"""Tests for late-stage anonymization and PII hardening."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.agents.nodes.sql_worker import sql_worker_node
from src.presentation.schemas.response import JobStatusResponse
from src.presentation.api.services.alerts import AlertService
from src.presentation.api.services.gamification import GamificationService
from src.infrastructure.extern.baml_client.types import GeneratedSQL
from src.domain.services.agent_metadata import AgentMetadataService
from src.utils.collections import BoundedDict

if TYPE_CHECKING:
    from src.infrastructure.agents.state import SQLTask


@pytest.mark.asyncio
async def test_sql_worker_node_dynamic_masking_viewer() -> None:
    """Verify sql_worker_node wraps the query with EXCLUDE for viewer role."""
    state: SQLTask = {
        'db_id': 'sis_db',
        'query_intent': 'Get student grades',
        'data': None,
        'sql': None,
        'error': None,
    }

    mock_metadata = MagicMock(spec=AgentMetadataService)
    mock_metadata.get_formatted_table_list = AsyncMock(return_value='students')
    mock_metadata.execute = AsyncMock(return_value=[{'col': 'val'}])

    config = {
        'configurable': {'metadata_service': mock_metadata, 'user_role': 'viewer'}
    }

    mock_sql_data = GeneratedSQL(
        sql='SELECT * FROM students',
        explanation='Testing',
        accessed_tables=['students'],
        dialect_used='duckdb',
    )

    with (
        patch('src.infrastructure.agents.nodes.sql_worker.b.GenerateSQL', return_value=mock_sql_data),
    ):
        result = await sql_worker_node(state, config)

        mock_metadata.execute.assert_called_once()
        called_db_id, called_sql = mock_metadata.execute.call_args[0]
        assert called_db_id == 'sis_db'
        # Verify that all PII columns are in the EXCLUDE clause
        assert 'EXCLUDE' in called_sql
        assert 'student_name' in called_sql
        assert 'email' in called_sql
        assert 'phone' in called_sql
        assert 'SELECT * FROM students' in called_sql
        assert result['results'][0]['data'] == [{'col': 'val'}]


@pytest.mark.asyncio
async def test_sql_worker_node_no_masking_admin() -> None:
    """Verify sql_worker_node does not wrap the query with EXCLUDE for admin role."""
    state: SQLTask = {
        'db_id': 'sis_db',
        'query_intent': 'Get all students',
        'data': None,
        'sql': None,
        'error': None,
    }

    mock_metadata = MagicMock(spec=AgentMetadataService)
    mock_metadata.get_formatted_table_list = AsyncMock(return_value='students')
    mock_metadata.execute = AsyncMock(return_value=[{'col': 'val'}])

    config = {'configurable': {'metadata_service': mock_metadata, 'user_role': 'admin'}}

    mock_sql_data = GeneratedSQL(
        sql='SELECT * FROM students',
        explanation='Testing',
        accessed_tables=['students'],
        dialect_used='duckdb',
    )

    with (
        patch('src.infrastructure.agents.nodes.sql_worker.b.GenerateSQL', return_value=mock_sql_data),
    ):
        result = await sql_worker_node(state, config)

        mock_metadata.execute.assert_called_once()
        called_db_id, called_sql = mock_metadata.execute.call_args[0]
        assert 'EXCLUDE' not in called_sql
        assert called_sql == 'SELECT * FROM students'


@pytest.mark.asyncio
async def test_email_draft_no_pii_to_ai(
    student_repository,
    advisor_repository,
    alert_repository,
    activity_repository,
    status_history_repository,
    test_db_session,
) -> None:
    """Verify that student PII is not sent directly to the AI draft generator."""
    sid = 'S001_SECRET'
    student_name = 'Real Name'
    email = 'real@ex.com'

    # Setup dummy student
    from src.infrastructure.database.models import Student, StudentStatusHistory

    student = Student(
        sid=sid,
        student_name=student_name,
        email=email,
        intervention_status='new',
    )
    test_db_session.add(student)

    # Setup dummy history
    history = StudentStatusHistory(
        history_id='1',
        sid=sid,
        academic_year=2024,
        semester=1,
        week=1,
        baseline_avg=85.0,
        baseline_std=5.0,
        current_score_avg=70.0,
        z_score=-3.0,
        anomaly_flag='Significant Drop',
    )
    test_db_session.add(history)
    await test_db_session.commit()

    job_id = 'test_job'
    jobs = BoundedDict[str, JobStatusResponse](maxsize=10)

    # In conftest, we don't have an idempotency_repository fixture yet, let's create it locally or use mock
    mock_idempotency = MagicMock()

    gamification_service = GamificationService(advisor_repository, student_repository)
    service = AlertService(
        alert_repository,
        MagicMock(),  # email_repo
        student_repository,
        mock_idempotency,
        gamification_service,
    )

    with patch(
        'src.presentation.api.services.alerts.b_async.GenerateDraftEmail',
        new_callable=AsyncMock,
    ) as mock_baml:
        mock_baml.return_value = 'Hello {{STUDENT_NAME}}'

        await service.run_email_draft_task(job_id, sid, jobs)

        # Check BAML was called
        mock_baml.assert_called_once()

        # Analyze the prompt context
        args, _kwargs = mock_baml.call_args
        context_sent_to_ai = args[1]  # context_str is the second arg

        # Verify performance data is there
        assert 'Score 70.0' in context_sent_to_ai
        # Verify PII is NOT there
        assert student_name not in context_sent_to_ai
        assert email not in context_sent_to_ai
