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
from src.domain.exceptions import (
    CaseAlreadyAssignedError,
    CaseNotFoundError,
    EmailNotFoundError,
    EmailUnavailableError,
    InvalidActionError,
    InvalidStateTransitionError,
    StudentNotFoundError,
    TimeSlotUnavailableError,
    UserIsNotAnAdvisorError,
)
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
    try:
        query = GetAllCasesQuery(user_id=user.id, limit=limit, offset=offset)
        return await query_handler.handle_get_all_cases(query)
    except Exception as e:
        logger.error('Failed to get all cases', error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        return await query_handler.handle_get_open_cases(query)
    except Exception as e:
        logger.error('Failed to get open cases list', error=str(e), exc_info=True)
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
        return await query_handler.handle_get_assigned_cases(query)
    except Exception as e:
        logger.error('Failed to get assigned cases list', error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/{case_id}')
async def get_case_details(
    case_id: str,
    query_handler: Annotated[CaseQueryHandler, Depends(get_case_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
) -> CaseDTO:
    """Retrieve full details of a specific case, including associated emails."""
    try:
        return await query_handler.handle_get_case_details(UUID(case_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error('Failed to get case details', case_id=case_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


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
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> TriggerDraftDTO:
    """Manually triggers a background AI draft generation."""
    try:
        if idempotency_key:
            idemp_key = UUID(idempotency_key)
            if await idempotency_repo.check_key(idemp_key):
                logger.info('Idempotency hit', operation='trigger_draft', idempotency_key=idemp_key)

                # return {
                #     'status': 'success',
                #     'message': 'Draft already triggered (idempotent).',
                # }

        command = TriggerDraftCommand(
            case_id=case_id,
            user_id=user.id,
        )
        result = await command_handler.handle_trigger_draft(command)

        if idempotency_key:
            await idempotency_repo.record_key(UUID(idempotency_key))

        if result.is_new_job:
            response.status_code = status.HTTP_202_ACCEPTED
        else:
            response.status_code = status.HTTP_200_OK

        return result
    except UserIsNotAnAdvisorError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except CaseNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidActionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/{case_id}/email')
async def get_email_draft(
    case_id: UUID,
    query_handler: Annotated[CaseQueryHandler, Depends(get_case_query_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
) -> QueryEmailDTO:
    """Retrieve the current AI draft status and content for a case."""
    try:
        return await query_handler.handle_get_case_email(case_id, user.id)
    except (CaseNotFoundError, EmailUnavailableError, EmailNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error('Failed to get email draft', case_id=case_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch('/{case_id}/email')
async def update_email_draft(
    case_id: UUID,
    request: UpdateEmailRequest,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
) -> dict[str, str]:
    """Manually update the subject or body of a draft email."""
    try:
        command = UpdateEmailCommand(
            case_id=case_id,
            user_id=user.id,
            subject=request.subject,
            body=request.body,
        )
        await command_handler.handle_update_email(command)
        return {'status': 'success', 'message': 'Draft updated'}
    except UserIsNotAnAdvisorError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except (CaseNotFoundError, EmailUnavailableError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (InvalidActionError, InvalidStateTransitionError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error('Failed to update email draft', case_id=case_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


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
    try:
        # 1. Early Return: Check idempotency
        if idemp_key and await idempotency_repo.check_key(idemp_key):
            raise HTTPException(status_code=200, detail='Email already sent (idempotent).')

        # 2. Database Write: Record state and get email address
        command = SendEmailCommand(case_id=case_id, user_id=user.id)
        result = await command_handler.handle_send_email(command)

        if idemp_key:
            await idempotency_repo.record_key(idemp_key)

        # 3. External I/O: Send the email AFTER the DB commit succeeds
        logger.info('Dispatching email job', case_id=case_id, job_id=result.job_id)

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error('Failed to send nudge email', case_id=case_id, error=str(e), exc_info=True)
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

    except CaseNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UserIsNotAnAdvisorError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except CaseAlreadyAssignedError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except StudentNotFoundError as e:
        logger.error('[Mismatch] A case exists without an associated student.')
        raise HTTPException(
            status_code=404,
            detail='Student information not found.',
        ) from e
    except Exception as e:
        logger.error('Failed to accept task', case_id=case_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/{case_id}/book')
async def book_appointment(
    case_id: UUID,
    request: BookAppointmentRequest,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
) -> ActionResponseDTO:
    """Allow a student to record that they have booked an appointment."""
    try:
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
    except CaseNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except TimeSlotUnavailableError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error('Failed to book appointment', case_id=case_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/{case_id}/supporting')
async def start_supporting(
    case_id: UUID,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
) -> ActionResponseDTO:
    """Advisor starts supporting the student after they booked."""
    try:
        command = StartSupportingCommand(case_id=case_id, user_id=user.id)
        await command_handler.handle_start_supporting(command)
        return ActionResponseDTO(
            status='success',
            message='Support session started successfully',
        )
    except UserIsNotAnAdvisorError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except CaseNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error('Failed to start supporting', case_id=case_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/{case_id}/resolve')
async def resolve_case(
    case_id: UUID,
    command_handler: Annotated[CaseCommandHandler, Depends(get_case_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.ALERTS_WRITE))],
) -> ActionResponseDTO:
    """Advisor marks the case as resolved."""
    try:
        command = ResolveCaseCommand(case_id=case_id, user_id=user.id)
        await command_handler.handle_resolve_case(command)
        return ActionResponseDTO(
            status='success',
            message='Resolution request sent to student',
        )
    except (CaseNotFoundError, UserIsNotAnAdvisorError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error('Failed to resolve case', case_id=case_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


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
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token has expired') from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='Invalid token') from None
    except CaseNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error('Failed to submit case review', error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
