"""Endpoint for polling background job status."""

from typing import Annotated

from arq import ArqRedis
from arq.jobs import Job
from fastapi import APIRouter, Depends, HTTPException

from src.domain.repositories.job_repository import JobRepository
from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.dependencies.providers import get_arq_pool, get_job_repository
from src.presentation.schemas.response import JobStatusResponse

router = APIRouter(prefix='/jobs', tags=['jobs'])


@router.get('/{job_id}', response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    _: Annotated[User, Depends(require_scope(Scope.JOBS_READ))],
    arq_pool: Annotated[ArqRedis, Depends(get_arq_pool)],
    job_repo: Annotated[JobRepository, Depends(get_job_repository)],
) -> JobStatusResponse:
    """Poll for the status and results of a background job."""
    # 1. Fetch from DB for observability
    from uuid import UUID
    db_job = await job_repo.get_job(UUID(job_id))
    
    # 2. Check ARQ for immediate status/result if needed
    job = Job(job_id, redis=arq_pool)
    arq_status = await job.status()

    if not db_job and arq_status == 'not_found':
        raise HTTPException(status_code=404, detail='Job not found')

    # Map status logic
    # Use DB status as primary if available, but respect ARQ for 'completed' result
    status = db_job['status'] if db_job else 'processing'
    if arq_status == 'complete':
        status = 'completed'
    elif arq_status == 'failed':
        status = 'failed'

    result = None
    if arq_status == 'complete':
        result = await job.result()

    return JobStatusResponse(
        job_id=job_id,
        status=status,
        progress=db_job.get('progress', 0) if db_job else 0,
        result=result,
        error=db_job.get('error_message') if db_job else None,
        created_at=db_job.get('created_at') if db_job else None,
        started_at=db_job.get('started_at') if db_job else None,
        completed_at=db_job.get('completed_at') if db_job else None,
    )
