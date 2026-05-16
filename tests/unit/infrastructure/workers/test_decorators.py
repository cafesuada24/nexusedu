
import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import BaseModel

from src.infrastructure.workers.framework.decorators import worker_task
from src.infrastructure.workers.framework.context import TaskContext

class MockPayload(BaseModel):
    job_id: str
    user_id: str

@pytest.mark.asyncio
async def test_worker_task_extracts_job_id_from_payload_kwarg():
    # Arrange
    job_id = str(uuid4())
    user_id = str(uuid4())
    payload = MockPayload(job_id=job_id, user_id=user_id)
    
    # Mock arq_ctx with a mock redis pool
    mock_redis = AsyncMock()
    arq_ctx = {"redis": mock_redis}
    
    # Mock task function
    mock_task = AsyncMock(return_value="success")
    
    # Apply decorator
    decorated_task = worker_task(track_job=True)(mock_task)
    
    # We need to mock the async_session_maker and JobTracker
    # But let's check if we can just verify the extraction logic by mocking the internal components
    
    with MagicMock() as mock_session_maker:
        from src.infrastructure.workers.framework import decorators
        import src.infrastructure.workers.framework.decorators as decorators_mod
        
        # Mock session and container
        mock_session = AsyncMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        
        # Patch async_session_maker
        decorators_mod.async_session_maker = mock_session_maker
        
        # We want to check if JobTracker was initialized with correct IDs
        with MagicMock() as mock_tracker_class:
            mock_tracker_instance = AsyncMock()
            mock_tracker_class.return_value = mock_tracker_instance
            decorators_mod.JobTracker = mock_tracker_class
            
            # Act
            await decorated_task(arq_ctx, payload=payload)
            
            # Assert
            mock_tracker_class.assert_called_once()
            args, kwargs = mock_tracker_class.call_args
            assert str(kwargs.get('job_id')) == job_id
            assert str(kwargs.get('user_id')) == user_id

@pytest.mark.asyncio
async def test_worker_task_extracts_job_id_from_args():
    # Arrange
    job_id = str(uuid4())
    user_id = str(uuid4())
    payload = MockPayload(job_id=job_id, user_id=user_id)
    
    mock_redis = AsyncMock()
    arq_ctx = {"redis": mock_redis}
    mock_task = AsyncMock(return_value="success")
    decorated_task = worker_task(track_job=True)(mock_task)
    
    from src.infrastructure.workers.framework import decorators as decorators_mod
    mock_session_maker = MagicMock()
    mock_session = AsyncMock()
    mock_session_maker.return_value.__aenter__.return_value = mock_session
    decorators_mod.async_session_maker = mock_session_maker
    
    with MagicMock() as mock_tracker_class:
        mock_tracker_instance = AsyncMock()
        mock_tracker_class.return_value = mock_tracker_instance
        decorators_mod.JobTracker = mock_tracker_class
        
        # Act - Pass payload as a positional argument (after arq_ctx which is handled by wrapper)
        await decorated_task(arq_ctx, payload)
        
        # Assert
        mock_tracker_class.assert_called_once()
        args, kwargs = mock_tracker_class.call_args
        assert str(kwargs.get('job_id')) == job_id
        assert str(kwargs.get('user_id')) == user_id
