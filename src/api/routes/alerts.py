"""API routes for Kanban Alert Dashboard management."""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.auth import User, check_role
from src.api.lifecycle import get_alert_service, get_jobs_store
from src.api.models.response import (
    EmailDraft,
    JobAcceptedResponse,
    JobStatusResponse,
)
from src.api.services.alerts import AlertService
from src.api.types import JobStore

router = APIRouter(prefix='/alerts', tags=['alerts'])


class AlertStudent(BaseModel):
    """Schema for a student in the Kanban alert dashboard."""

    sid: str = Field(..., description='Student identifier.')
    student_name: str = Field(..., description='Student name.')
    email: str = Field(..., description='Student email.')
    current_risk_status: str = Field(..., description='The type of anomaly detected.')
    intervention_status: str = Field(..., description='The current Kanban state.')


class StatusUpdate(BaseModel):
    """Schema for updating a student's intervention status."""

    status: str = Field(..., description='The new Kanban state.')


class DraftRequest(BaseModel):
    """Schema for requesting a personalized email draft."""

    booking_link: str | None = Field(
        None,
        description='Custom booking link to use in the draft.',
    )


class SendEmailRequest(BaseModel):
    """Schema for sending a personalized nudge email."""

    body: str = Field(..., description='The final email body to send.')


@router.get('/', response_model=list[AlertStudent])
async def get_alerts(
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    _user: Annotated[User, Depends(check_role('advisor:read'))],
    status: str | None = Query(None),
) -> list[dict[str, str]]:
    """Retrieve students who have an active alert for the Kanban board.

    Args:
        alert_service: The alert service dependency.
        _user: Authenticated user with read access.
        status: Optional status filter.

    Returns:
        List of students with active alerts.
    """
    if status:
        valid_statuses = ['new', 'sent', 'booked', 'supporting', 'resolved', 'expired']
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f'Invalid status filter. Must be one of {valid_statuses}',
            )

    try:
        return alert_service.get_alerts(status)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch('/{sid}/status')
async def update_alert_status(
    sid: str,
    update: StatusUpdate,
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    user: Annotated[User, Depends(check_role('advisor:write'))],
) -> dict[str, str]:
    """Manually transitions a student's Kanban state.

    Args:
        sid: Student identifier.
        update: The status update request.
        alert_service: The alert service dependency.
        user: Authenticated user with write access.

    Returns:
        The updated status summary.
    """
    try:
        alert_service.update_status(sid, update.status, str(user.id))
        return {'sid': sid, 'new_status': update.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/{sid}/draft/review')
async def review_draft(
    sid: str,
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    user: Annotated[User, Depends(check_role('advisor:write'))],
) -> dict[str, str]:
    """Explicitly rewards the advisor for reviewing the LLM draft.

    Args:
        sid: Student identifier.
        alert_service: The alert service dependency.
        user: Authenticated user with write access.

    Returns:
        Success message.
    """
    try:
        alert_service.award_review_points(sid, str(user.id))
        return {'status': 'success', 'message': 'Draft review points awarded.'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/{sid}/draft', response_model=JobAcceptedResponse, status_code=202)
async def generate_email_draft(  # noqa: PLR0913
    sid: str,
    background_tasks: BackgroundTasks,
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    user: Annotated[User, Depends(check_role('advisor:write'))],
    jobs: Annotated[JobStore, Depends(get_jobs_store)],
    request: DraftRequest | None = None,
) -> JobAcceptedResponse:
    """Triggers the AI to generate a personalized email draft in the background.

    Args:
        sid: Student identifier.
        background_tasks: FastAPI background tasks.
        alert_service: The alert service dependency.
        user: Authenticated user with write access.
        jobs: The job store dependency.
        request: The draft request details.

    Returns:
        A job acceptance response with job_id.
    """
    job_id = str(uuid.uuid4())
    booking_link = request.booking_link if request else None

    # Initialize job status
    jobs[job_id] = JobStatusResponse(job_id=job_id, status='processing')

    # Schedule background task
    background_tasks.add_task(
        alert_service.run_email_draft_task,
        job_id=job_id,
        sid=sid,
        jobs=jobs,
        booking_link=booking_link,
        user_id=str(user.id),
    )

    return JobAcceptedResponse(job_id=job_id, status='processing')


@router.post('/{sid}/send')
async def send_nudge_email(
    sid: str,
    request: SendEmailRequest,
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    user: Annotated[User, Depends(check_role('advisor:write'))],
) -> dict[str, str]:
    """Dispatches the email and updates the intervention lifecycle.

    Args:
        sid: Student identifier.
        request: The email sending request.
        alert_service: The alert service dependency.
        user: Authenticated user with write access.

    Returns:
        Success message.
    """
    try:
        email = alert_service.send_email(sid, request.body, str(user.id))
        return {'status': 'success', 'message': f'Email sent to {email}'}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
