"""Case repository interface."""

from typing import Protocol
from uuid import UUID

from src.domain.entities.case import Case, TaskItemRecord
from src.domain.value_objects.status import CaseStatus


class CaseRepository(Protocol):
    """Interface for managing student cases."""

    async def create_case(self, case: Case) -> None:
        """Create a new case."""
        ...

    async def get_active_case(self, sid: UUID) -> Case | None:
        """Retrieve the active case for a student, if any."""
        ...

    async def update_case_status(self, case_id: UUID, status: CaseStatus) -> None:
        """Update the status of a case."""
        ...

    async def get_by_id(self, case_id: UUID) -> Case | None:
        """Retrieve a case by its ID."""
        ...

    async def get_student_cases(self, sid: UUID) -> list[Case]:
        """Retrieve all cases for a specific student."""
        ...

    async def assign_case(self, case_id: UUID, advisor_id: UUID) -> bool:
        """Assign an advisor to a case. Returns True if successful, False if already assigned."""
        ...

    async def get_task_list(
        self,
        advisor_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[TaskItemRecord], int]:
        """Retrieve task list table for advisors with pagination.
        
        Returns:
            Tuple of (list of records, total count)
        """
        ...
