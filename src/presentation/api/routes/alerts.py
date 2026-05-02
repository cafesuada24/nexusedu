"""API routes for Kanban Alert Dashboard management."""

from typing import Annotated, Any
from uuid import UUID

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
)
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.value_objects.status import InterventionStatus
from src.infrastructure.database.session import get_async_session
from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.dependencies.providers import (
    get_alert_command_handler,
    get_alert_query_handler,
    get_case_repository,
    get_email_repository,
)
from src.presentation.schemas.request import SendEmailRequest, StatusUpdate
from src.presentation.schemas.response import AlertStudent, CaseResponse
from src.core.logger import logger

router = APIRouter(prefix='/alerts', tags=['alerts'])


@router.get('/{sid}/cases', response_model=list[CaseResponse])
async def get_case_history(
    sid: str,
    case_repo: Annotated[CaseRepository, Depends(get_case_repository)],
    _: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
) -> list[dict[str, Any]]:
    """Retrieve historical cases for a specific student."""
    try:
        cases = await case_repo.get_student_cases(UUID(sid))
        return [
            {
                'case_id': str(c.case_id),
                'sid': str(c.sid),
                'status': c.status.value,
                'created_at': c.created_at.isoformat(),
                'resolved_at': c.resolved_at.isoformat() if c.resolved_at else None,
            }
            for c in cases
        ]
    except Exception as e:
        logger.error(f'Error in get_case_history: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/cases/{case_id}')
async def get_case_details(
    case_id: str,
    query_handler: Annotated[AlertQueryHandler, Depends(get_alert_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
) -> dict[str, Any]:
    """Retrieve full details of a specific case, including associated emails."""
    try:
        return await query_handler.handle_get_case_details(UUID(case_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f'Error in get_case_details: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('', response_model=list[AlertStudent])
async def get_alerts(
    query_handler: Annotated[AlertQueryHandler, Depends(get_alert_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
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
                'is_generating': d.student.is_generating,
                'active_case_id': str(d.student.active_case_id)
                if d.student.active_case_id
                else None,
            }
            for d in dtos
        ]
    except Exception as e:
        logger.error(f'Error in get_alerts: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch('/cases/{case_id}/status')
async def update_alert_status(
    case_id: str,
    update: StatusUpdate,
    command_handler: Annotated[AlertCommandHandler, Depends(get_alert_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, str]:
    """Manually transitions a student's Kanban state."""
    try:
        status = InterventionStatus(update.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail='Invalid status.') from e

    try:
        if idempotency_key:
            idemp_key = UUID(idempotency_key)
            if await command_handler.check_idempotency(idemp_key):
                logger.info(f'Idempotency hit for update_alert_status: {idemp_key}')
                return {'case_id': case_id, 'new_status': update.status}

        command = UpdateStudentStatusCommand(
            case_id=UUID(case_id),
            status=status,
            user_id=user.id,
        )
        await command_handler.handle_update_status(command)

        if idempotency_key:
            await command_handler.record_idempotency(UUID(idempotency_key))

        return {'case_id': case_id, 'new_status': update.status}
    except Exception as e:
        logger.error(f'Error in update_alert_status: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


class TriggerDraftRequest(BaseModel):
    """Schema for triggering a background AI draft generation."""

    booking_link: str | None = Field(None, description='Optional custom booking link.')


@router.post('/cases/{case_id}/draft', status_code=202)
async def trigger_draft(
    case_id: str,
    request: TriggerDraftRequest,
    command_handler: Annotated[AlertCommandHandler, Depends(get_alert_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, str]:
    """Manually triggers a background AI draft generation."""
    try:
        if idempotency_key:
            idemp_key = UUID(idempotency_key)
            if await command_handler.check_idempotency(idemp_key):
                logger.info(f'Idempotency hit for trigger_draft: {idemp_key}')
                return {
                    'status': 'success',
                    'message': 'Draft already triggered (idempotent).',
                }

        command = TriggerDraftCommand(
            case_id=UUID(case_id), user_id=user.id, booking_link=request.booking_link,
        )
        job_id = await command_handler.handle_trigger_draft(command)

        if idempotency_key:
            await command_handler.record_idempotency(UUID(idempotency_key))

        return {'status': 'success', 'job_id': str(job_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/cases/{case_id}/draft/review')
async def review_draft(
    case_id: str,
    command_handler: Annotated[AlertCommandHandler, Depends(get_alert_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, str]:
    """Explicitly rewards the advisor for reviewing the LLM draft."""
    try:
        if idempotency_key:
            idemp_key = UUID(idempotency_key)
            if await command_handler.check_idempotency(idemp_key):
                logger.info(f'Idempotency hit for review_draft: {idemp_key}')
                return {
                    'status': 'success',
                    'message': 'Draft review points already awarded (idempotent).',
                }

        # Note: Idempotency logic should ideally be in command handler
        command = AwardReviewPointsCommand(case_id=UUID(case_id), user_id=user.id)
        await command_handler.handle_award_review_points(command)

        if idempotency_key:
            await command_handler.record_idempotency(UUID(idempotency_key))

        return {'status': 'success', 'message': 'Draft review points awarded.'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/cases/{case_id}/draft')
async def get_email_draft(
    case_id: str,
    query_handler: Annotated[AlertQueryHandler, Depends(get_alert_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
) -> dict[str, Any]:
    """Retrieve the current AI draft status and content for a case."""
    try:
        return await query_handler.handle_get_draft_status(UUID(case_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f'Error in get_email_draft: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/cases/{case_id}/email')
async def get_case_email(
    case_id: str,
    email_repo: Annotated[EmailRepository, Depends(get_email_repository)],
    _: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
) -> dict[str, Any] | None:
    """Retrieve the single intervention email associated with a specific case."""
    try:
        email = await email_repo.get_by_case(UUID(case_id))
        if not email:
            return None

        return {
            'email_id': str(email.email_id),
            'subject': email.subject,
            'body': email.body,
            'status': email.status.value,
            'created_at': email.created_at.isoformat(),
            'sent_at': email.sent_at.isoformat() if email.sent_at else None,
        }
    except Exception as e:
        logger.error(f'Error in get_case_email: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/cases/{case_id}/send')
async def send_nudge_email(
    case_id: str,
    request: SendEmailRequest,
    command_handler: Annotated[AlertCommandHandler, Depends(get_alert_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, str]:
    """Dispatches the email and updates the intervention lifecycle."""
    idemp_key = UUID(idempotency_key) if idempotency_key else None
    try:
        # 1. Early Return: Check idempotency
        if idemp_key and await command_handler.check_idempotency(idemp_key):
            return {
                'status': 'success',
                'message': 'Email already sent (idempotent).',
            }

        # 2. Database Write: Record state and get email address
        command = SendEmailCommand(
            case_id=UUID(case_id),
            body=request.body,
            user_id=user.id,
        )
        target_email = await command_handler.handle_send_email(command)

        if idemp_key:
            await command_handler.record_idempotency(idemp_key)

        # Explicitly commit the transaction before performing external I/O
        await session.commit()

        # 3. External I/O: Send the email AFTER the DB commit succeeds
        logger.info(
            f'DISPATCHING EMAIL for case {case_id} to {target_email}: {request.body[:50]}...',
        )

        return {'status': 'success', 'message': f'Email sent to {target_email}'}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f'Error in send_nudge_email: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
