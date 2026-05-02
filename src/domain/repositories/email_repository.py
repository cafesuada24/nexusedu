"""Email repository interface."""

from typing import Protocol
from uuid import UUID

from src.domain.entities.intervention_email import InterventionEmail


class EmailRepository(Protocol):
    """Interface for managing intervention emails."""

    async def get_latest_draft(self, sid: UUID) -> InterventionEmail | None:
        """Retrieve the latest draft email for a student."""
        ...

    async def create_draft(
        self,
        sid: UUID,
        advisor_id: UUID | None,
        subject: str,
        body: str,
        case_id: UUID | None = None,
    ) -> UUID:
        """Create a new draft email and return its ID."""
        ...

    async def mark_as_sent(self, sid: UUID, body: str) -> None:
        """Mark the latest draft as sent for a student."""
        ...

    async def get_history(self, sid: UUID) -> list[InterventionEmail]:
        """Retrieve the communication history for a student."""
        ...
