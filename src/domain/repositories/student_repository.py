"""Student repository interface."""

from typing import Any, Protocol

from src.core.identifiers import EntityID
from src.domain.entities.student import Student


class StudentRepository(Protocol):
    """Interface for student-related data operations."""

    async def get_by_id(self, sid: EntityID) -> Student:
        """Retrieve a student by their unique ID."""
        ...

    async def save(self, student: Student) -> None:
        """Update student information."""
        ...

    async def get_recent_performance(
        self,
        sid: EntityID,
        limit: int = 4,
    ) -> list[dict[str, Any]]:
        """Retrieve recent performance history for a student."""
        ...

    async def ingest_students(self, records: list[dict[str, Any]]) -> None:
        """Bulk ingest student records."""
        ...
