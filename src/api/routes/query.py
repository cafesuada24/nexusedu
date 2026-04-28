"""Main endpoint for agent interaction."""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from src.api.auth import User, check_role
from src.api.lifecycle import get_jobs_store, get_query_service
from src.api.models.request import QueryRequest
from src.api.models.response import (
    JobAcceptedResponse,
    JobStatusResponse,
)
from src.api.services.query import QueryService
from src.api.types import JobStore

router = APIRouter(tags=['agent'])


@router.post('/query', response_model=JobAcceptedResponse, status_code=202)
async def process_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    query_service: Annotated[QueryService, Depends(get_query_service)],
    user: Annotated[User, Depends(check_role('advisor:read'))],
    jobs: Annotated[JobStore, Depends(get_jobs_store)],
) -> JobAcceptedResponse:
    """Triggers the LangGraph agent in the background.

    Returns a job_id immediately for status polling.
    """
    job_id = str(uuid.uuid4())

    # Initialize job status
    jobs[job_id] = JobStatusResponse(job_id=job_id, status='processing')

    # Schedule background task
    background_tasks.add_task(
        query_service.run_agent_task,
        job_id=job_id,
        query=request.query,
        thread_id=request.thread_id,
        user=user,
        jobs=jobs,
    )

    return JobAcceptedResponse(job_id=job_id, status='processing')
