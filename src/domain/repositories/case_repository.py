"""Case repository interface."""

from typing import Protocol
from uuid import UUID

from src.domain.entities.case import Case


class CaseRepository(Protocol):
    """Interface for managing student cases."""

    async def create_case(self, case: Case) -> None:
        """Create a new case."""
        ...

    async def get_active_case(self, sid: UUID) -> Case | None:
        """Retrieve the active case for a student, if any."""
        ...

    async def update_case_status(self, case_id: UUID, status: str) -> None:
        """Update the status of a case."""
        ...

    async def get_by_id(self, case_id: UUID) -> Case | None:
        """Retrieve a case by its ID."""
        ...

    async def get_student_cases(self, sid: UUID) -> list[Case]:
        """Retrieve all cases for a specific student."""
        ...

    async def assign_case(self, case_id: UUID, advisor_id: UUID) -> None:
        """Assign an advisor to a case."""
        ...
