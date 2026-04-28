"""Endpoint for polling background job status."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.api.auth import User, check_role
from src.api.lifecycle import get_jobs_store
from src.api.models.response import JobStatusResponse
from src.api.types import JobStore

router = APIRouter(prefix='/jobs', tags=['jobs'])


@router.get('/{job_id}', response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    _: Annotated[User, Depends(check_role('advisor:read'))],
    jobs: Annotated[JobStore, Depends(get_jobs_store)],
) -> JobStatusResponse:
    """Poll for the status and results of a background job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail='Job not found')
    return jobs[job_id]
