"""API routes for Kanban Alert Dashboard management."""

from typing import Annotated, Any

from arq import ArqRedis
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import Scope, User, require_scope
from src.api.lifecycle import get_alert_service, get_arq_pool, get_jobs_store
from src.api.services.alerts import AlertService
from src.api.types import JobStore
from src.database.session import get_async_session

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


class SendEmailRequest(BaseModel):
    """Schema for sending a personalized nudge email."""

    body: str = Field(..., description='The final email body to send.')


@router.get('', response_model=list[AlertStudent])
async def get_alerts(
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    _user: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
    status: str | None = Query(None),
) -> list[dict[str, Any]]:
    """Retrieve students who have an active alert for the Kanban board."""
    if status:
        valid_statuses = ['new', 'sent', 'booked', 'supporting', 'resolved', 'expired']
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f'Invalid status filter. Must be one of {valid_statuses}',
            )

    try:
        return await alert_service.get_alerts(status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch('/{sid}/status')
async def update_alert_status(
    sid: str,
    update: StatusUpdate,
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict[str, str]:
    """Manually transitions a student's Kanban state."""
    try:
        async with session.begin():
            await alert_service.update_status(sid, update.status, str(user.id))
        return {'sid': sid, 'new_status': update.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/{sid}/draft/trigger', status_code=202)
async def trigger_draft(
    sid: str,
    arq_pool: Annotated[ArqRedis | None, Depends(get_arq_pool)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    jobs: Annotated[JobStore, Depends(get_jobs_store)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict[str, str]:
    """Manually triggers a background AI draft generation."""
    try:
        async with session.begin():
            job_id = await alert_service.trigger_draft(
                sid=sid,
                arq_pool=arq_pool,
                jobs=jobs,
                user_id=str(user.id),
            )
        return {'status': 'success', 'job_id': job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/{sid}/draft/review')
async def review_draft(
    sid: str,
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, str]:
    """Explicitly rewards the advisor for reviewing the LLM draft."""
    try:
        async with session.begin():
            if idempotency_key and await alert_service.check_idempotency(idempotency_key):
                return {
                    'status': 'success',
                    'message': 'Draft review points already awarded (idempotent).',
                }

            await alert_service.award_review_points(sid, str(user.id))

            if idempotency_key:
                await alert_service.record_idempotency(idempotency_key)

        return {'status': 'success', 'message': 'Draft review points awarded.'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/{sid}/draft')
async def get_email_draft(
    sid: str,
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    _user: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
) -> dict[str, Any]:
    """Retrieve the current AI draft status and content for a student."""
    try:
        is_generating = await alert_service.get_draft_status(sid)
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
    """Retrieve communication history for a specific student."""
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
    session: Annotated[AsyncSession, Depends(get_async_session)],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, str]:
    """Dispatches the email and updates the intervention lifecycle."""
    try:
        async with session.begin():
            if idempotency_key and await alert_service.check_idempotency(idempotency_key):
                return {
                    'status': 'success',
                    'message': 'Email already sent (idempotent).',
                }

            email = await alert_service.send_email(sid, request.body, str(user.id))

            if idempotency_key:
                await alert_service.record_idempotency(idempotency_key)

        return {'status': 'success', 'message': f'Email sent to {email}'}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
