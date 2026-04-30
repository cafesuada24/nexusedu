"""Endpoint for polling background job status."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.api.types import JobStore
from src.presentation.dependencies.providers import get_jobs_store
from src.presentation.schemas.response import JobStatusResponse

router = APIRouter(prefix='/jobs', tags=['jobs'])


@router.get('/{job_id}', response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    _: Annotated[User, Depends(require_scope(Scope.JOBS_READ))],
    jobs: Annotated[JobStore, Depends(get_jobs_store)],
) -> JobStatusResponse:
    """Poll for the status and results of a background job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail='Job not found')
    return jobs[job_id]
