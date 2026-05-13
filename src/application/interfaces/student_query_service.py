"""Student query service interface."""

from typing import Protocol

from src.application.dtos.pagination import PagedResponse
from src.application.dtos.student_dtos import StudentDTO, StudentTermMetricsDTO
from src.core.identifiers import EntityID


class StudentQueryService(Protocol):
    """Interface for student-related query operations."""

    async def get_all_students(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> PagedResponse[StudentDTO]:
        """Retrieve a paginated list of students."""
        ...

    async def get_student(self, sid: EntityID) -> StudentDTO:
        """Retrieve a single student by ID."""
        ...

    async def get_student_term_metrics(
        self,
        sid: EntityID,
        academic_year: int | None = None,
        semester: int | None = None,
    ) -> StudentTermMetricsDTO:
        """Retrieve term-based metrics and course details for a student."""
        ...
