"""Activity repository interface."""

from typing import Any, Protocol


from src.core.identifiers import EntityID


class ActivityRepository(Protocol):
    """Interface for assessment activity operations."""

    async def ingest_activities(self, records: list[dict[str, Any]]) -> None:
        """Bulk ingest activity records."""
        ...

    async def get_weekly_averages(self) -> list[dict[str, Any]]:
        """Retrieve average scores per student per week."""
        ...

    async def get_student_term_metrics(
        self,
        sid: EntityID,
        academic_year: int | None = None,
        semester: int | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve term-based metrics and course details for a student."""
        ...
