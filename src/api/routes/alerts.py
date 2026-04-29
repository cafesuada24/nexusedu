"""API routes for Kanban Alert Dashboard management."""

from typing import Annotated, Any

from arq import ArqRedis
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.auth import Scope, User, require_scope
from src.api.lifecycle import get_alert_service, get_arq_pool, get_jobs_store
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
    draft_job_id: str | None = Field(
        None,
        description='Background Job ID for the AI draft.',
    )


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


@router.get('', response_model=list[AlertStudent])
async def get_alerts(
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    _user: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
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
        return await alert_service.get_alerts(status)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch('/{sid}/status')
async def update_alert_status(
    sid: str,
    update: StatusUpdate,
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
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
        await alert_service.update_status(sid, update.status, str(user.id))
        return {'sid': sid, 'new_status': update.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/{sid}/draft/review')
async def review_draft(
    sid: str,
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, str]:
    """Explicitly rewards the advisor for reviewing the LLM draft.

    Args:
        sid: Student identifier.
        alert_service: The alert service dependency.
        user: Authenticated user with write access.
        idempotency_key: Optional idempotency key to prevent duplicate awards.

    Returns:
        Success message.
    """
    if idempotency_key:
        if await alert_service.db.check_idempotency_async(idempotency_key):
            return {
                'status': 'success',
                'message': 'Draft review points already awarded (idempotent).',
            }
        await alert_service.db.record_idempotency_async(idempotency_key)

    try:
        await alert_service.award_review_points(sid, str(user.id))
        return {'status': 'success', 'message': 'Draft review points awarded.'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/{sid}/draft')
async def get_email_draft(
    sid: str,
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    _user: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
) -> dict[str, Any]:
    """Retrieve the current AI draft status and content for a student.

    Returns:
        The draft subject and body if available, plus generation status.
    """
    try:
        # Check if currently generating
        student = await alert_service.db.execute_async(
            'sis_db', 'SELECT draft_job_id FROM students WHERE sid = ?', (sid,)
        )
        is_generating = bool(student and student[0].get('draft_job_id'))

        # Fetch latest draft
        drafts = await alert_service.get_email_history(sid)
        latest_draft = next((d for d in drafts if d['status'] == 'draft'), None)

        return {
            'sid': sid,
            'is_generating': is_generating,
            'subject': latest_draft['subject'] if latest_draft else None,
            'body': latest_draft['body'] if latest_draft else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/{sid}/history')
async def get_alert_history(
    sid: str,
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    _user: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
) -> list[dict[str, Any]]:
    """Retrieve communication history for a specific student.

    Args:
        sid: Student identifier.
        alert_service: The alert service dependency.

    Returns:
        List of historical communication entries.
    """
    try:
        return await alert_service.get_email_history(sid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/{sid}/send')
async def send_nudge_email(
    sid: str,
    request: SendEmailRequest,
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, str]:
    """Dispatches the email and updates the intervention lifecycle.

    Args:
        sid: Student identifier.
        request: The email sending request.
        alert_service: The alert service dependency.
        user: Authenticated user with write access.
        idempotency_key: Optional idempotency key to prevent duplicate sends.

    Returns:
        Success message.
    """
    if idempotency_key:
        if await alert_service.db.check_idempotency_async(idempotency_key):
            return {'status': 'success', 'message': 'Email already sent (idempotent).'}
        await alert_service.db.record_idempotency_async(idempotency_key)

    try:
        email = await alert_service.send_email(sid, request.body, str(user.id))
        return {'status': 'success', 'message': f'Email sent to {email}'}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
