"""Email repository interface."""

from typing import Protocol
from uuid import UUID

from src.domain.entities.intervention_email import InterventionEmail


class EmailRepository(Protocol):
    """Interface for managing intervention emails."""

    async def add(self, email: InterventionEmail) -> None:
        """Add an intervention email."""
        ...

    async def save(self, email: InterventionEmail) -> None:
        """Update the content and status of an existing case email."""
        ...

    async def get_by_case(self, case_id: UUID) -> InterventionEmail:
        """Find the email associated with a specific case."""
        ...

    async def find_by_case(self, case_id: UUID) -> InterventionEmail | None:
        """Retrieve the email associated with a specific case."""
        ...
