"""API routes for student management."""

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.application.dtos.pagination import PagedResponse
from src.application.dtos.student_dtos import (
    GetAllStudentsQuery,
    GetStudentQuery,
    StudentDTO,
)
from src.application.queries.student_queries import StudentQueryHandler
from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.dependencies.providers import get_student_query_handler

logger = structlog.get_logger(__name__)

router = APIRouter(prefix='/students', tags=['students'])


@router.get('/')
async def get_all_students(
    query_handler: Annotated[StudentQueryHandler, Depends(get_student_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.STUDENTS_READ))],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PagedResponse[StudentDTO]:
    """Retrieve all students in the system."""
    try:
        query = GetAllStudentsQuery(limit=limit, offset=offset)
        return await query_handler.handle_get_all_students(query)
    except Exception as e:
        logger.error('Error fetching students', error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An unexpected error occurred while fetching students.',
        ) from e


@router.get('/{sid}')
async def get_student(
    sid: UUID,
    query_handler: Annotated[StudentQueryHandler, Depends(get_student_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.STUDENTS_READ))],
) -> StudentDTO:
    """Retrieve details for a specific student."""
    try:
        query = GetStudentQuery(sid=sid)
        return await query_handler.handle_get_student(query)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error('Error in get_student', error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An unexpected error occurred while fetching student details.',
        ) from e
