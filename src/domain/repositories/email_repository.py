"""Email repository interface."""

from typing import Protocol

from src.core.identifiers import EntityID
from src.domain.entities.intervention_email import InterventionEmail


class EmailRepository(Protocol):
    """Interface for managing intervention emails."""

    async def add(self, email: InterventionEmail) -> None:
        """Add an intervention email."""
        ...

    async def save(self, email: InterventionEmail) -> None:
        """Update the content and status of an existing case email."""
        ...

    async def get_by_case(self, case_id: EntityID) -> InterventionEmail:
        """Find the email associated with a specific case."""
        ...

    async def find_by_case(self, case_id: EntityID) -> InterventionEmail | None:
        """Retrieve the email associated with a specific case."""
        ...
