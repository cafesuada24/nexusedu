"""Endpoint for polling background job status."""

from typing import Annotated

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException

from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.dependencies.providers import get_arq_pool
from src.presentation.schemas.response import JobStatusResponse

router = APIRouter(prefix='/jobs', tags=['jobs'])


@router.get('/{job_id}', response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    _: Annotated[User, Depends(require_scope(Scope.JOBS_READ))],
    arq_pool: Annotated[ArqRedis, Depends(get_arq_pool)],
) -> JobStatusResponse:
    """Poll for the status and results of a background job."""
    job = await arq_pool.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')

    status = await job.status()

    # Map ARQ JobStatus to our JobStatusResponse status
    # arq.jobs.JobStatus: deferred, queued, in_progress, complete, failed
    mapped_status = 'processing'
    if status == 'complete':
        mapped_status = 'completed'
    elif status == 'failed':
        mapped_status = 'failed'
    elif status in ('queued', 'deferred', 'in_progress'):
        mapped_status = 'processing'

    result = None
    error = None

    if mapped_status == 'completed':
        result = await job.result()
    elif mapped_status == 'failed':
        try:
            await job.result()
        except Exception as e:
            error = str(e)

    return JobStatusResponse(
        job_id=job_id,
        status=mapped_status,
        result=result,
        error=error,
    )
