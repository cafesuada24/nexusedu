import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, UTC
import contextlib

from src.infrastructure.workers.tasks.ai_tasks import (
    run_batch_case_overviews_task,
    run_generate_case_overview_task,
)
from src.application.dtos.worker_payloads.ai_payloads import GenerateCaseOverviewPayload
from src.domain.value_objects.status import InterventionStatus

@pytest.mark.asyncio
async def test_run_batch_case_overviews_task_fan_out():
    # Mock context
    ctx = {"redis": MagicMock()}
    
    # Mock session and result
    mock_session = AsyncMock()
    
    # Mock result for select(OrmCase.case_id)
    case_id = uuid4()
    mock_result = MagicMock()
    mock_result.all.return_value = [(case_id,)]
    mock_session.execute.return_value = mock_result
    
    @contextlib.asynccontextmanager
    async def mock_session_maker():
        yield mock_session

    with patch("src.infrastructure.workers.framework.decorators.async_session_maker", side_effect=mock_session_maker):
        with patch("src.infrastructure.workers.framework.decorators.Container") as MockContainer:
            container = MockContainer.return_value
            uow = AsyncMock()
            uow.__aenter__.return_value = uow
            container.uow = uow
            
            # Run task
            await run_batch_case_overviews_task(ctx)
            
            # Verify fan-out via UoW
            uow.enqueue.assert_called_once()
            call_args = uow.enqueue.call_args
            assert call_args.args[0] == 'run_generate_case_overview_task'
            payload = call_args.kwargs['payload']
            assert isinstance(payload, GenerateCaseOverviewPayload)
            assert payload.case_id == case_id
            uow.commit.assert_called_once()

@pytest.mark.asyncio
async def test_run_generate_case_overview_task_success():
    # Mock context
    ctx = {"redis": MagicMock()}
    case_id = uuid4()
    payload = GenerateCaseOverviewPayload(case_id=case_id)
    
    # Mock session
    mock_session = AsyncMock()
    
    @contextlib.asynccontextmanager
    async def mock_session_maker():
        yield mock_session

    with patch("src.infrastructure.workers.framework.decorators.async_session_maker", side_effect=mock_session_maker):
        with patch("src.infrastructure.workers.framework.decorators.Container") as MockContainer:
            container = MockContainer.return_value
            case_repo = AsyncMock()
            student_query_service = AsyncMock()
            uow = AsyncMock()
            
            container.case_repo = case_repo
            container.student_query_service = student_query_service
            container.uow = uow
            
            # Mock case domain entity
            mock_case = MagicMock()
            mock_case.sid = uuid4()
            case_repo.get_by_id.return_value = mock_case
            uow.cases.get_by_id.return_value = mock_case
            
            # Mock student metrics
            mock_metrics = MagicMock()
            mock_metrics.model_dump_json.return_value = '{"test": "data"}'
            student_query_service.get_student_term_metrics.return_value = mock_metrics
            
            # Mock BAML
            with patch("src.infrastructure.workers.tasks.ai_tasks.b") as mock_b:
                mock_overview = MagicMock()
                mock_overview.academic_summary = "Test summary"
                mock_overview.action_keys = ["Key 1", "Key 2"]
                mock_b.GenerateCaseOverview = AsyncMock(return_value=mock_overview)
                
                # Run task
                await run_generate_case_overview_task(ctx, payload)
                
                # Verify
                case_repo.get_by_id.assert_called_once_with(case_id)
                student_query_service.get_student_term_metrics.assert_called_once_with(sid=mock_case.sid)
                mock_b.GenerateCaseOverview.assert_called_once()
                mock_case.set_ai_overview.assert_called_once_with(
                    summary="Test summary",
                    keys=["Key 1", "Key 2"]
                )
                uow.cases.save.assert_called_once_with(mock_case)
                uow.commit.assert_called_once()
