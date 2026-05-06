"""API routes for Student Case management."""

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.case_commands import (
    AcceptCaseCommand,
    AwardReviewPointsCommand,
    CaseCommandHandler,
    SendEmailCommand,
    TriggerDraftCommand,
    UpdateStudentStatusCommand,
)
from src.application.dtos.case_dtos import CaseDTO
from src.application.queries.case_queries import (
    CaseQueryHandler,
    GetAssignedQuery,
    GetUnassignedQuery,
)
from src.core.logger import logger
from src.domain.repositories.advisor_repository import AdvisorRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.idempotency_repository import IdempotencyRepository
from src.domain.value_objects.status import InterventionStatus
from src.infrastructure.database.session import get_async_session
from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.dependencies.providers import (
    get_case_command_handler,
    get_case_query_handler,
    get_email_repository,
    get_idempotency_repository,
)
from src.presentation.dtos.pagination import PagedResponse, PaginationMetadata
from src.presentation.schemas.request import SendEmailRequest, StatusUpdate

router = APIRouter(prefix='/cases', tags=['cases'])



@router.get('/open')
async def get_open_cases_list(
    query_handler: Annotated[CaseQueryHandler, Depends(get_case_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.CASE_READ))],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PagedResponse[CaseDTO]:
    """Retrieve the unified list of cases for the advisor dashboard.

    Administrators see all open cases. Advisors see new cases (unassigned)
    and cases specifically assigned to them.
    """
    try:
        query = GetUnassignedQuery(limit=limit, offset=offset)
        cases, total_count = await query_handler.handle_get_open_cases(query)

        return PagedResponse[CaseDTO](
            items=cases,
            metadata=PaginationMetadata(
                total_count=total_count,
                limit=limit,
                offset=offset,
                has_next=offset + len(cases) < total_count,
            ),
        )
    except Exception as e:
        logger.error(f'Error in get_case_list: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get('/assigned')
async def get_assigned_cases_list(
    query_handler: Annotated[CaseQueryHandler, Depends(get_case_query_handler)],
    user: Annotated[User, Depends(require_scope(Scope.CASE_READ))],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PagedResponse[CaseDTO]:
    """Retrieve the unified list of cases for the advisor dashboard.

    Administrators see all open cases. Advisors see new cases (unassigned)
    and cases specifically assigned to them.
    """
    try:
        query = GetAssignedQuery(user_id=user.id, limit=limit, offset=offset)
        cases, total_count = await query_handler.handle_get_assigned_cases(query)

        return PagedResponse[CaseDTO](
            items=cases,
            metadata=PaginationMetadata(
                total_count=total_count,
                limit=limit,
                offset=offset,
                has_next=offset + len(cases) < total_count,
            ),
        )
    except Exception as e:
        logger.error(f'Error in get_case_list: {str(e)}', exc_info=True)
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
        IdempotencyRepository,
        Depends(get_idempotency_repository),
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
    case_id: UUID,
    request: TriggerDraftRequest,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    idempotency_repo: Annotated[
        IdempotencyRepository, Depends(get_idempotency_repository)
    ],
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
            case_id=case_id,
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
        IdempotencyRepository,
        Depends(get_idempotency_repository),
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
    case_id: UUID,
    query_handler: Annotated[CaseQueryHandler, Depends(get_case_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
) -> dict[str, Any]:
    """Retrieve the current AI draft status and content for a case."""
    try:
        return await query_handler.handle_get_draft_status(case_id)
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
    idempotency_repo: Annotated[
        IdempotencyRepository,
        Depends(get_idempotency_repository),
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


@router.post('/{case_id}/accept')
async def accept_task(
    case_id: UUID,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.CASE_ACCEPT))],
) -> dict[str, str]:
    """An advisor accept to solve a case."""
    try:
        command = AcceptCaseCommand(
            case_id=case_id,
            user_id=user.id,
            accepted_at=datetime.now(UTC),
        )
        await command_handler.handle_accept_case(command)
        return {'status': 'success', 'task_id': str(case_id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        logger.error(f'Error in complete_task: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
