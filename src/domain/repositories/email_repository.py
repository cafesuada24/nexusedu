"""Email repository interface."""

from typing import Protocol
from uuid import UUID

from src.domain.entities.intervention_email import InterventionEmail


class EmailRepository(Protocol):
    """Interface for managing intervention emails."""

    async def create_placeholder(
        self,
        case_id: UUID,
        sid: UUID,
        advisor_id: UUID | None,
    ) -> UUID:
        """Create a placeholder email with 'generating' status."""
        ...

    async def update_content(
        self,
        case_id: UUID,
        subject: str,
        body: str,
        status: str,
    ) -> None:
        """Update the content and status of an existing case email."""
        ...

    async def get_by_case(self, case_id: UUID) -> InterventionEmail | None:
        """Retrieve the email associated with a specific case."""
        ...

    async def mark_as_sent(self, case_id: UUID, body: str) -> None:
        """Mark the case email as sent."""
        ...

    async def get_history(self, sid: UUID) -> list[InterventionEmail]:
        """Retrieve the communication history for a student."""
        ...
