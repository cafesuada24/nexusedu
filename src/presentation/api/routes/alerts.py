"""API routes for Kanban Alert Dashboard management."""

from typing import Annotated, Any
from uuid import UUID

from arq import ArqRedis
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.alert_commands import (
    AlertCommandHandler,
    AwardReviewPointsCommand,
    SendEmailCommand,
    TriggerDraftCommand,
    UpdateStudentStatusCommand,
)
from src.application.queries.alert_queries import (
    AlertQueryHandler,
    GetActiveAlertsQuery,
    GetEmailHistoryQuery,
)
from src.domain.value_objects.status import InterventionStatus
from src.infrastructure.database.session import get_async_session
from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.dependencies.providers import (
    get_alert_command_handler,
    get_alert_query_handler,
    get_arq_pool,
)
from src.telemetry.logger import logger

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
    query_handler: Annotated[AlertQueryHandler, Depends(get_alert_query_handler)],
    _user: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
    status: str | None = Query(None),
) -> list[dict[str, Any]]:
    """Retrieve students who have an active alert for the Kanban board."""
    if status:
        try:
            InterventionStatus(status)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail='Invalid status filter. Must be a valid InterventionStatus.',
            ) from e

    try:
        query = GetActiveAlertsQuery(status_filter=status)
        dtos = await query_handler.handle_get_active_alerts(query)
        # Map DTOs to response schema
        return [
            {
                'sid': str(d.student.sid),
                'student_name': d.student.student_name,
                'email': d.student.email,
                'current_risk_status': d.student.current_risk_status.value,
                'intervention_status': d.student.intervention_status.value,
                'draft_job_id': d.alert_details.get('draft_job_id'),
            }
            for d in dtos
        ]
    except Exception as e:
        logger.error(f'Error in get_alerts: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch('/{sid}/status')
async def update_alert_status(
    sid: str,
    update: StatusUpdate,
    command_handler: Annotated[AlertCommandHandler, Depends(get_alert_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
) -> dict[str, str]:
    """Manually transitions a student's Kanban state."""
    try:
        status = InterventionStatus(update.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail='Invalid status.') from e

    try:
        command = UpdateStudentStatusCommand(
            sid=UUID(sid),
            status=status,
            user_id=user.id,
        )
        await command_handler.handle_update_status(command)
        return {'sid': sid, 'new_status': update.status}
    except Exception as e:
        logger.error(f'Error in update_alert_status: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/{sid}/draft/trigger', status_code=202)
async def trigger_draft(
    sid: str,
    command_handler: Annotated[AlertCommandHandler, Depends(get_alert_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict[str, str]:
    """Manually triggers a background AI draft generation."""
    try:
        command = TriggerDraftCommand(sid=UUID(sid), user_id=user.id)
        job_id = await command_handler.handle_trigger_draft(command)
        return {'status': 'success', 'job_id': str(job_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/{sid}/draft/review')
async def review_draft(
    sid: str,
    command_handler: Annotated[AlertCommandHandler, Depends(get_alert_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, str]:
    """Explicitly rewards the advisor for reviewing the LLM draft."""
    try:
        # Note: Idempotency logic should ideally be in command handler
        command = AwardReviewPointsCommand(sid=UUID(sid), user_id=user.id)
        await command_handler.handle_award_review_points(command)

        return {'status': 'success', 'message': 'Draft review points awarded.'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/{sid}/draft')
async def get_email_draft(
    sid: str,
    query_handler: Annotated[AlertQueryHandler, Depends(get_alert_query_handler)],
    _user: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
) -> dict[str, Any]:
    """Retrieve the current AI draft status and content for a student."""
    try:
        return await query_handler.handle_get_draft_status(UUID(sid))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/{sid}/history')
async def get_alert_history(
    sid: str,
    query_handler: Annotated[AlertQueryHandler, Depends(get_alert_query_handler)],
    _user: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
) -> list[dict[str, Any]]:
    """Retrieve communication history for a specific student."""
    try:
        query = GetEmailHistoryQuery(sid=UUID(sid))
        dtos = await query_handler.handle_get_email_history(query)
        return [
            {
                'email_id': d.email_id,
                'subject': d.subject,
                'body': d.body,
                'status': d.status,
                'created_at': d.created_at,
                'sent_at': d.sent_at,
            }
            for d in dtos
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/{sid}/send')
async def send_nudge_email(
    sid: str,
    request: SendEmailRequest,
    command_handler: Annotated[AlertCommandHandler, Depends(get_alert_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, str]:
    """Dispatches the email and updates the intervention lifecycle."""
    idemp_key = UUID(idempotency_key)
    try:
        # 1. Early Return: Check idempotency
        if idempotency_key and await command_handler.check_idempotency(idemp_key):
            return {
                'status': 'success',
                'message': 'Email already sent (idempotent).',
            }

        # 2. Database Write: Record state and get email address
        command = SendEmailCommand(
            sid=UUID(sid), body=request.body, user_id=user.id
        )
        target_email = await command_handler.handle_send_email(command)

        if idempotency_key:
            await command_handler.record_idempotency(idemp_key)

        # Explicitly commit the transaction before performing external I/O
        await session.commit()

        # 3. External I/O: Send the email AFTER the DB commit succeeds
        # In a real app, this might be another port/service call
        logger.info(f'DISPATCHING EMAIL to {target_email}: {request.body[:50]}...')

        return {'status': 'success', 'message': f'Email sent to {target_email}'}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
