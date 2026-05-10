"""Student query service interface."""

from typing import Protocol
from uuid import UUID

from src.application.dtos.pagination import PagedResponse
from src.application.dtos.student_dtos import StudentDTO


class StudentQueryService(Protocol):
    """Interface for student-related query operations."""

    async def get_all_students(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> PagedResponse[StudentDTO]:
        """Retrieve a paginated list of students."""
        ...

    async def get_student(self, sid: UUID) -> StudentDTO:
        """Retrieve a single student by ID."""
        ...
