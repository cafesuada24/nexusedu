"""API routes for Student Case management."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import jwt
import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status

from src.application.commands.case_commands import (
    AcceptCaseCommand,
    BookAppointmentCommand,
    CaseCommandHandler,
    SendEmailCommand,
    SubmitCaseReviewCommand,
    TriggerDraftCommand,
    UpdateEmailCommand,
)
from src.application.dtos.case_dtos import (
    ActionResponseDTO,
    CaseDTO,
    GetAllCasesQuery,
    QueryEmailDTO,
    ResolveCaseCommand,
    ReviewCaseDTO,
    SendEmailResponseDTO,
    StartSupportingCommand,
    TriggerDraftDTO,
)
from src.application.dtos.pagination import PagedResponse
from src.application.queries.case_queries import (
    CaseQueryHandler,
    GetAssignedQuery,
    GetUnassignedQuery,
)
from src.core.config import config
from src.domain.repositories.idempotency_repository import IdempotencyRepository
from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.dependencies.providers import (
    get_case_command_handler,
    get_case_query_handler,
    get_idempotency_repository,
)
from src.presentation.schemas.request import BookAppointmentRequest, UpdateEmailRequest

logger = structlog.get_logger(__name__)


router = APIRouter(prefix='/cases', tags=['cases'])


@router.get('')
async def get_all_cases(
    query_handler: Annotated[CaseQueryHandler, Depends(get_case_query_handler)],
    user: Annotated[User, Depends(require_scope(Scope.CASE_READ_ALL))],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PagedResponse[CaseDTO]:
    """Retrieve all cases in the system (Admin only)."""
    query = GetAllCasesQuery(user_id=user.id, limit=limit, offset=offset)
    return await query_handler.handle_get_all_cases(query)


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
    query = GetUnassignedQuery(limit=limit, offset=offset)
    return await query_handler.handle_get_open_cases(query)


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
    query = GetAssignedQuery(user_id=user.id, limit=limit, offset=offset)
    return await query_handler.handle_get_assigned_cases(query)


@router.get('/{case_id}')
async def get_case_details(
    case_id: UUID,
    query_handler: Annotated[CaseQueryHandler, Depends(get_case_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
) -> CaseDTO:
    """Retrieve full details of a specific case, including associated emails."""
    return await query_handler.handle_get_case_details(case_id)


@router.post('/{case_id}/email/draft')
async def trigger_draft(
    case_id: UUID,
    response: Response,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    idempotency_repo: Annotated[
        IdempotencyRepository,
        Depends(get_idempotency_repository),
    ],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    idempotency_key: Annotated[UUID | None, Header(alias='Idempotency-Key')] = None,
) -> TriggerDraftDTO:
    """Manually triggers a background AI draft generation."""
    if idempotency_key and await idempotency_repo.check_key(idempotency_key):
        logger.info(
            'Idempotency hit',
            operation='trigger_draft',
            idempotency_key=idempotency_key,
        )
        # Using 200 for idempotent hits is a choice, though some prefer 204 or just returning the result.
        raise HTTPException(200, 'email already triggered.')

    command = TriggerDraftCommand(
        case_id=case_id,
        user_id=user.id,
    )
    result = await command_handler.handle_trigger_draft(command)

    if idempotency_key:
        await idempotency_repo.record_key(idempotency_key)

    if result.is_new_job:
        response.status_code = status.HTTP_202_ACCEPTED
    else:
        response.status_code = status.HTTP_200_OK

    return result


@router.get('/{case_id}/email')
async def get_email_draft(
    case_id: UUID,
    query_handler: Annotated[CaseQueryHandler, Depends(get_case_query_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
) -> QueryEmailDTO:
    """Retrieve the current AI draft status and content for a case."""
    return await query_handler.handle_get_case_email(case_id, user.id)


@router.patch('/{case_id}/email')
async def update_email_draft(
    case_id: UUID,
    request: UpdateEmailRequest,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
) -> dict[str, str]:
    """Manually update the subject or body of a draft email."""
    command = UpdateEmailCommand(
        case_id=case_id,
        user_id=user.id,
        subject=request.subject,
        body=request.body,
    )
    await command_handler.handle_update_email(command)
    return {'status': 'success', 'message': 'Draft updated'}


@router.post('/{case_id}/email/send')
async def send_nudge_email(
    case_id: UUID,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
    idempotency_repo: Annotated[
        IdempotencyRepository,
        Depends(get_idempotency_repository),
    ],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> SendEmailResponseDTO:
    """Dispatches the email and updates the intervention lifecycle."""
    idemp_key = UUID(idempotency_key) if idempotency_key else None

    # 1. Early Return: Check idempotency
    if idemp_key and await idempotency_repo.check_key(idemp_key):
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail='Email already sent (idempotent).',
        )

    # 2. Database Write: Record state and get email address
    command = SendEmailCommand(case_id=case_id, user_id=user.id)
    result = await command_handler.handle_send_email(command)

    if idemp_key:
        await idempotency_repo.record_key(idemp_key)

    # 3. External I/O: Send the email AFTER the DB commit succeeds
    logger.info('Dispatching email job', case_id=case_id, job_id=result.job_id)

    return result


@router.post('/{case_id}/accept')
async def accept_task(
    case_id: UUID,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.CASE_ACCEPT))],
) -> dict[str, str]:
    """An advisor accept to solve a case."""
    command = AcceptCaseCommand(
        case_id=case_id,
        user_id=user.id,
        accepted_at=datetime.now(UTC),
    )
    await command_handler.handle_accept_case(command)
    return {'status': 'success', 'task_id': str(case_id)}


@router.post('/{case_id}/book')
async def book_appointment(
    case_id: UUID,
    request: BookAppointmentRequest,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
) -> ActionResponseDTO:
    """Allow a student to record that they have booked an appointment."""
    command = BookAppointmentCommand(
        case_id=case_id,
        appointment_time=request.appointment_time,
        meeting_method=request.meeting_method,
        notes=request.notes,
    )
    await command_handler.handle_book_appointment(command)
    return ActionResponseDTO(
        status='success',
        message='Appointment booked successfully',
    )


@router.post('/{case_id}/supporting')
async def start_supporting(
    case_id: UUID,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
) -> ActionResponseDTO:
    """Advisor starts supporting the student after they booked."""
    command = StartSupportingCommand(case_id=case_id, user_id=user.id)
    await command_handler.handle_start_supporting(command)
    return ActionResponseDTO(
        status='success',
        message='Support session started successfully',
    )


@router.post('/{case_id}/resolve')
async def resolve_case(
    case_id: UUID,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
) -> ActionResponseDTO:
    """Advisor marks the case as resolved."""
    command = ResolveCaseCommand(case_id=case_id, user_id=user.id)
    await command_handler.handle_resolve_case(command)
    return ActionResponseDTO(
        status='success',
        message='Resolution request sent to student',
    )


@router.post('/review')
async def submit_case_review(
    token: Annotated[str, Query(...)],
    request: ReviewCaseDTO,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
) -> ActionResponseDTO:
    """Student submits a review for a case resolution."""
    try:
        # 1. Verify JWT token
        payload = jwt.decode(token, config.jwt_secret, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token has expired',
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token',
        ) from None

    case_id = UUID(payload['case_id'])

    # 2. Execute command
    command = SubmitCaseReviewCommand(
        case_id=case_id,
        satisfaction=request.satisfaction,
        comment=request.comment,
    )
    await command_handler.handle_submit_case_review(command)

    return ActionResponseDTO(
        status='success',
        message='Review submitted successfully',
    )
