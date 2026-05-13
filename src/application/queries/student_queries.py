"""Query handlers for student-related operations."""

from src.application.dtos.pagination import PagedResponse
from src.application.dtos.student_dtos import (
    GetAllStudentsQuery,
    GetStudentQuery,
    GetStudentTermMetricsQuery,
    StudentDTO,
    StudentTermMetricsDTO,
)
from src.application.interfaces.student_query_service import StudentQueryService


class StudentQueryHandler:
    """Handler for student-related queries."""

    def __init__(
        self,
        student_query_service: StudentQueryService,
    ):
        """Initialize with required query service."""
        self._student_query_service = student_query_service

    async def handle_get_all_students(
        self,
        query: GetAllStudentsQuery,
    ) -> PagedResponse[StudentDTO]:
        """Execute the get all students query."""
        return await self._student_query_service.get_all_students(
            limit=query.limit,
            offset=query.offset,
        )

    async def handle_get_student(
        self,
        query: GetStudentQuery,
    ) -> StudentDTO:
        """Execute the get student query."""
        return await self._student_query_service.get_student(sid=query.sid)

    async def handle_get_student_term_metrics(
        self,
        query: GetStudentTermMetricsQuery,
    ) -> StudentTermMetricsDTO:
        """Execute the get student term metrics query."""
        return await self._student_query_service.get_student_term_metrics(
            sid=query.sid,
            academic_year=query.academic_year,
            semester=query.semester,
        )
