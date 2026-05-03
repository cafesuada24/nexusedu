"""API routes for Student Case management."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.case_commands import (
    AwardReviewPointsCommand,
    CaseCommandHandler,
    SendEmailCommand,
    TriggerDraftCommand,
    UpdateStudentStatusCommand,
)
from src.application.queries.case_queries import (
    CaseQueryHandler,
    GetTaskListQuery,
)
from src.core.logger import logger
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.idempotency_repository import IdempotencyRepository
from src.domain.value_objects.status import InterventionStatus
from src.infrastructure.database.session import get_async_session
from src.presentation.api.auth import Scope, User, UserRole, require_scope
from src.presentation.dependencies.providers import (
    get_case_command_handler,
    get_case_query_handler,
    get_case_repository,
    get_email_repository,
    get_idempotency_repository,
)
from src.presentation.schemas.request import SendEmailRequest, StatusUpdate
from src.presentation.schemas.response import (
    CaseResponse,
    TaskPagedResponse,
)

router = APIRouter(prefix='/cases', tags=['cases'])


@router.get('/student/{sid}', response_model=list[CaseResponse])
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


@router.get('', response_model=TaskPagedResponse)
async def get_cases_list(
    query_handler: Annotated[CaseQueryHandler, Depends(get_case_query_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Retrieve the unified list of cases for the advisor dashboard.

    Administrators see all open cases. Advisors see new cases (unassigned)
    and cases specifically assigned to them.
    """
    try:
        advisor_id = None if user.role == UserRole.ADMIN.value else user.id
        query = GetTaskListQuery(advisor_id=advisor_id, limit=limit, offset=offset)
        paged_dto = await query_handler.handle_get_task_list(query)

        return {
            'items': [
                {
                    'case_id': str(d.case_id),
                    'created_at': d.created_at.isoformat() + 'Z',
                    'assigned_advisor_id': str(d.assigned_advisor_id)
                    if d.assigned_advisor_id
                    else None,
                    'student_name': d.student_name,
                    'email': d.email,
                    'major': d.major,
                    'current_risk_status': d.current_risk_status.value,
                    'intervention_status': d.intervention_status.value,
                    'draft_subject': d.draft_subject,
                    'draft_body': d.draft_body,
                    'draft_status': d.draft_status,
                    'assigned_to': d.assigned_to,
                    'suggested_action': d.suggested_action,
                    'points_reward': d.points_reward,
                }
                for d in paged_dto.items
            ],
            'metadata': {
                'total_count': paged_dto.metadata.total_count,
                'limit': paged_dto.metadata.limit,
                'offset': paged_dto.metadata.offset,
                'has_next': paged_dto.metadata.has_next,
            },
        }
    except Exception as e:
        logger.error(f'Error in get_task_list: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/{case_id}')
async def get_case_details(
    case_id: str,
    query_handler: Annotated[CaseQueryHandler, Depends(get_case_query_handler)],
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


@router.patch('/{case_id}/status')
async def update_case_status(
    case_id: str,
    update: StatusUpdate,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    idempotency_repo: Annotated[
        IdempotencyRepository, Depends(get_idempotency_repository),
    ],
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
            if await idempotency_repo.check_key(idemp_key):
                logger.info(f'Idempotency hit for update_case_status: {idemp_key}')
                return {'case_id': case_id, 'new_status': update.status}

        command = UpdateStudentStatusCommand(
            case_id=UUID(case_id),
            status=status,
            user_id=user.id,
        )
        await command_handler.handle_update_status(command)

        if idempotency_key:
            await idempotency_repo.record_key(UUID(idempotency_key))

        return {'case_id': case_id, 'new_status': update.status}
    except Exception as e:
        logger.error(f'Error in update_case_status: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


class TriggerDraftRequest(BaseModel):
    """Schema for triggering a background AI draft generation."""

    booking_link: str | None = Field(None, description='Optional custom booking link.')


@router.post('/{case_id}/email/draft', status_code=202)
async def trigger_draft(
    case_id: str,
    request: TriggerDraftRequest,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    idempotency_repo: Annotated[IdempotencyRepository, Depends(get_idempotency_repository)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, str]:
    """Manually triggers a background AI draft generation."""
    try:
        if idempotency_key:
            idemp_key = UUID(idempotency_key)
            if await idempotency_repo.check_key(idemp_key):
                logger.info(f'Idempotency hit for trigger_draft: {idemp_key}')
                return {
                    'status': 'success',
                    'message': 'Draft already triggered (idempotent).',
                }

        command = TriggerDraftCommand(
            case_id=UUID(case_id),
            user_id=user.id,
            booking_link=request.booking_link,
        )
        job_id = await command_handler.handle_trigger_draft(command)

        if idempotency_key:
            await idempotency_repo.record_key(UUID(idempotency_key))

        return {'status': 'success', 'job_id': str(job_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/{case_id}/email/draft/review')
async def review_draft(
    case_id: str,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    idempotency_repo: Annotated[
        IdempotencyRepository, Depends(get_idempotency_repository),
    ],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, str]:
    """Explicitly rewards the advisor for reviewing the LLM draft."""
    try:
        if idempotency_key:
            idemp_key = UUID(idempotency_key)
            if await idempotency_repo.check_key(idemp_key):
                logger.info(f'Idempotency hit for review_draft: {idemp_key}')
                return {
                    'status': 'success',
                    'message': 'Draft review points already awarded (idempotent).',
                }

        command = AwardReviewPointsCommand(case_id=UUID(case_id), user_id=user.id)
        await command_handler.handle_award_review_points(command)

        if idempotency_key:
            await idempotency_repo.record_key(UUID(idempotency_key))

        return {'status': 'success', 'message': 'Draft review points awarded.'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/{case_id}/email/draft')
async def get_email_draft(
    case_id: str,
    query_handler: Annotated[CaseQueryHandler, Depends(get_case_query_handler)],
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


@router.get('/{case_id}/email')
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


@router.post('/{case_id}/email/send')
async def send_nudge_email(
    case_id: str,
    request: SendEmailRequest,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    idempotency_repo: Annotated[
        IdempotencyRepository, Depends(get_idempotency_repository),
    ],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, str]:
    """Dispatches the email and updates the intervention lifecycle."""
    idemp_key = UUID(idempotency_key) if idempotency_key else None
    try:
        # 1. Early Return: Check idempotency
        if idemp_key and await idempotency_repo.check_key(idemp_key):
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
            await idempotency_repo.record_key(idemp_key)

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
