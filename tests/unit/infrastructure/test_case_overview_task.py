import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, UTC
from src.worker import run_batch_case_overviews_task
from src.domain.value_objects.status import InterventionStatus

@pytest.mark.asyncio
async def test_run_batch_case_overviews_task_success():
    # Mock context
    ctx = {"redis": MagicMock()}
    
    # Mock session and result
    mock_session = AsyncMock()
    mock_orm_case = MagicMock()
    mock_orm_case.case_id = uuid4()
    mock_orm_case.sid = uuid4()
    mock_orm_case.intervention_status = InterventionStatus.NEW
    mock_orm_case.academic_summary = None
    mock_orm_case.action_keys = None
    mock_orm_case.version = 0
    mock_orm_case.created_at = datetime.now(UTC)
    mock_orm_case.appointment = None
    mock_orm_case.assigned_at = None
    mock_orm_case.closed_at = None
    mock_orm_case.assigned_advisor_id = None
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_orm_case]
    mock_session.execute.return_value = mock_result
    
    # Mock Container and Services
    with patch("src.worker.get_async_session") as mock_get_session:
        # get_async_session is an async generator
        async def async_gen():
            yield mock_session
        mock_get_session.return_value = async_gen()
        
        with patch("src.worker.Container") as MockContainer:
            container = MockContainer.return_value
            case_repo = container.case_repo
            student_query_service = container.student_query_service
            
            # Mock student metrics
            mock_metrics = MagicMock()
            mock_metrics.model_dump_json.return_value = '{"test": "data"}'
            student_query_service.get_student_term_metrics = AsyncMock(return_value=mock_metrics)
            
            # Mock BAML
            with patch("src.worker.b") as mock_b:
                mock_overview = MagicMock()
                mock_overview.academic_summary = "Test summary"
                mock_overview.action_keys = ["Key 1", "Key 2"]
                mock_b.GenerateCaseOverview = AsyncMock(return_value=mock_overview)
                
                # Run task
                await run_batch_case_overviews_task(ctx)
                
                # Verify
                student_query_service.get_student_term_metrics.assert_called_once_with(sid=mock_orm_case.sid)
                mock_b.GenerateCaseOverview.assert_called_once()
                case_repo.save.assert_called_once()
                mock_session.commit.assert_called_once()
