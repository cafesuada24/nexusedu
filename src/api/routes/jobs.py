"""Endpoint for polling background job status."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.api.auth import User, check_role
from src.api.models.response import JobStatusResponse
from src.api.utils.jobs_store import _jobs

router = APIRouter(prefix='/jobs', tags=['jobs'])


@router.get('/{job_id}', response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    user: Annotated[User, Depends(check_role('advisor:read'))],
) -> JobStatusResponse:
    """Poll for the status and results of a background job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail='Job not found')
    return _jobs[job_id]
