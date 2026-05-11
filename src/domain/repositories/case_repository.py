"""Case repository interface."""

from datetime import datetime
from typing import Protocol

from src.core.identifiers import EntityID
from src.domain.entities.case import Case


class CaseRepository(Protocol):
    """Interface for managing student cases."""

    async def add(self, case: Case) -> None:
        """Add a case."""
        ...

    async def get_active_case(self, sid: EntityID) -> Case | None:
        """Retrieve the active case for a student, if any."""
        ...

    async def get_by_id(self, case_id: EntityID) -> Case:
        """Retrieve a case by its ID."""
        ...

    async def find_by_id(self, case_id: EntityID) -> Case | None:
        """Find a case by its ID."""
        ...

    async def get_student_cases(self, sid: EntityID) -> list[Case]:
        """Retrieve all cases for a specific student."""
        ...

    async def assign_case(self, case_id: EntityID, advisor_id: EntityID) -> bool:
        """Assign an advisor to a case. Returns True if successful, False if already assigned."""
        ...

    async def save(self, case: Case) -> None:
        """Update a case."""
        ...

    async def has_overlapping_appointment(
        self,
        advisor_id: EntityID,
        appointment_time: datetime,
    ) -> bool:
        """Check if an advisor already has an appointment at the given time."""
        ...
