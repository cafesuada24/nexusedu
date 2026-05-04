"""Tests for late-stage anonymization and PII hardening."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.commands.case_commands import (
    CaseCommandHandler,
    GenerateEmailDraftCommand,
)
from src.application.services.agent_metadata import AgentMetadataService
from src.domain.services.gamification import GamificationService
from src.infrastructure.agents.nodes.sql_worker import sql_worker_node
from src.infrastructure.extern.baml_client.types import GeneratedSQL

if TYPE_CHECKING:
    from src.infrastructure.agents.state import SQLTask


@pytest.mark.asyncio
async def test_sql_worker_node_dynamic_masking_viewer() -> None:
    """Verify sql_worker_node wraps the query with EXCLUDE for viewer role."""
    state: SQLTask = {
        "db_id": "sis_db",
        "query_intent": "Get student grades",
        "data": None,
        "sql": None,
        "error": None,
    }

    mock_metadata = MagicMock(spec=AgentMetadataService)
    mock_metadata.get_formatted_table_list = AsyncMock(return_value="students")
    mock_metadata.execute = AsyncMock(return_value=[{"col": "val"}])

    config = {
        "configurable": {"metadata_service": mock_metadata, "user_role": "viewer"}
    }

    mock_sql_data = GeneratedSQL(
        sql="SELECT * FROM students",
        explanation="Testing",
        accessed_tables=["students"],
        dialect_used="duckdb",
    )

    with (
        patch(
            "src.infrastructure.agents.nodes.sql_worker.b.GenerateSQL",
            return_value=mock_sql_data,
        ),
    ):
        result = await sql_worker_node(state, config)

        mock_metadata.execute.assert_called_once()
        called_db_id, called_sql = mock_metadata.execute.call_args[0]
        assert called_db_id == "sis_db"
        # Verify that all PII columns are in the EXCLUDE clause
        assert "EXCLUDE" in called_sql
        assert "student_name" in called_sql
        assert "email" in called_sql
        assert "phone" in called_sql
        assert "SELECT * FROM students" in called_sql
        assert result["results"][0]["data"] == [{"col": "val"}]


@pytest.mark.asyncio
async def test_sql_worker_node_no_masking_admin() -> None:
    """Verify sql_worker_node does not wrap the query with EXCLUDE for admin role."""
    state: SQLTask = {
        "db_id": "sis_db",
        "query_intent": "Get all students",
        "data": None,
        "sql": None,
        "error": None,
    }

    mock_metadata = MagicMock(spec=AgentMetadataService)
    mock_metadata.get_formatted_table_list = AsyncMock(return_value="students")
    mock_metadata.execute = AsyncMock(return_value=[{"col": "val"}])

    config = {"configurable": {"metadata_service": mock_metadata, "user_role": "admin"}}

    mock_sql_data = GeneratedSQL(
        sql="SELECT * FROM students",
        explanation="Testing",
        accessed_tables=["students"],
        dialect_used="duckdb",
    )

    with (
        patch(
            "src.infrastructure.agents.nodes.sql_worker.b.GenerateSQL",
            return_value=mock_sql_data,
        ),
    ):
        result = await sql_worker_node(state, config)

        mock_metadata.execute.assert_called_once()
        called_db_id, called_sql = mock_metadata.execute.call_args[0]
        assert "EXCLUDE" not in called_sql
        assert called_sql == "SELECT * FROM students"


@pytest.mark.asyncio
async def test_email_draft_no_pii_to_ai(
    student_repository,
    advisor_repository,
    alert_repository,
    case_repository,
    activity_repository,
    status_history_repository,
    test_db_session,
) -> None:
    """Verify that student PII is not sent directly to the AI draft generator."""
    sid = uuid4()
    cid = uuid4()
    student_name = "Real Name"
    email = "real@ex.com"

    # Setup dummy student
    from src.infrastructure.database.models import (
        Student,
        StudentStatusHistory,
    )

    student = Student(
        sid=sid,
        student_name=student_name,
        email=email,
        intervention_status="new",
    )
    test_db_session.add(student)

    # Setup dummy case
    from src.domain.entities.case import Case
    await case_repository.create_case(Case(case_id=cid, sid=sid))

    # Setup dummy history
    history = StudentStatusHistory(
        history_id=uuid4(),
        sid=sid,
        academic_year=2024,
        semester=1,
        week=1,
        baseline_avg=85.0,
        baseline_std=5.0,
        current_score_avg=70.0,
        z_score=-3.0,
        anomaly_flag="Significant Drop",
    )
    test_db_session.add(history)
    await test_db_session.commit()

    job_id = uuid4()

    # In conftest, we don't have an idempotency_repository fixture yet, let's create it locally or use mock
    mock_idempotency = MagicMock()

    gamification_service = GamificationService()

    mock_email_drafting = AsyncMock()
    mock_email_drafting.generate_draft = AsyncMock(return_value="Hello {{STUDENT_NAME}}")

    mock_task_queue = AsyncMock()

    handler = CaseCommandHandler(
        student_repo=student_repository,
        email_repo=AsyncMock(),
        case_repo=case_repository,
        job_repo=AsyncMock(),
        advisor_repo=advisor_repository,
        gamification_service=gamification_service,
        task_queue=mock_task_queue,
        email_drafting_service=mock_email_drafting,
    )

    command = GenerateEmailDraftCommand(case_id=cid, job_id=job_id)
    await handler.handle_generate_email_draft(command)

    # Check email drafting was called
    mock_email_drafting.generate_draft.assert_called_once()

    # Analyze the prompt context
    args, _kwargs = mock_email_drafting.generate_draft.call_args
    # args[0] is student_name, args[1] is context_str, args[2] is booking_link
    context_sent_to_ai = args[1]

    # Verify performance data is there
    assert "Score 70.0" in context_sent_to_ai
    # Verify PII is NOT there (except the name which is passed as a separate argument for templating)
    # Actually, in the implementation of handle_generate_email_draft:
    # personalized_body = await self.email_drafting_service.generate_draft(
    #     student_data['student_name'], context_str, booking_link
    # )
    # So student_name IS passed to generate_draft, but not in the context_str.
    assert student_name not in context_sent_to_ai
    assert email not in context_sent_to_ai
