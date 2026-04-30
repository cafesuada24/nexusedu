"""API routes for agent queries."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.api.services.query import QueryService
from src.presentation.api.types import JobStore
from src.presentation.dependencies.providers import (
    get_arq_pool,
    get_jobs_store,
    get_query_service,
)
from src.presentation.schemas.response import JobStatusResponse

router = APIRouter(prefix='/query', tags=['query'])


@router.post('', status_code=202)
async def submit_query(
    query: str,
    background_tasks: BackgroundTasks,
    query_service: Annotated[QueryService, Depends(get_query_service)],
    jobs: Annotated[JobStore, Depends(get_jobs_store)],
    user: Annotated[User, Depends(require_scope(Scope.QUERY_EXECUTE))],
    thread_id: str | None = Query(None, description='Existing thread identifier.'),
) -> dict[str, str]:
    """Submits a natural language query for processing by the agent.

    The query is processed in the background, and a job ID is returned to track status.
    """
    job_id = str(uuid.uuid4())

    # Initialize job status
    jobs[job_id] = JobStatusResponse(job_id=job_id, status='processing')

    # User info for agent context
    user_dict = {
        'id': str(user.id),
        'role': user.role,
        'email': user.email,
    }

    # Run in background
    background_tasks.add_task(
        query_service.run_agent_task,
        job_id=job_id,
        query=query,
        thread_id=thread_id,
        user_dict=user_dict,
        jobs=jobs,
    )

    return {'job_id': job_id}
