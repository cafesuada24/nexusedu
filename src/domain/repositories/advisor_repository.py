"""Advisor repository interface."""

from typing import Any, Protocol
from uuid import UUID

from src.domain.entities.advisor import Advisor


class AdvisorRepository(Protocol):
    """Interface for advisor-related data operations."""

    async def upsert_advisor_for_user(
        self,
        user_id: UUID,
        email: str,
        name: str,
    ) -> None:
        """Link a user to an advisor profile, creating one if necessary."""
        ...

    async def get_by_id(self, advisor_id: UUID) -> Advisor:
        """Retrieve an advisor by their unique ID."""
        ...

    async def find_by_id(self, advisor_id: UUID) -> Advisor | None:
        """Find an advisor by their unique ID."""
        ...

    async def find_by_user_id(self, user_id: UUID) -> Advisor | None:
        """Find an advisor by their associated user ID."""
        ...

    async def get_by_user_id(self, user_id: UUID) -> Advisor:
        """Retrieve an advisor by their associated user ID."""
        ...

    async def save(self, advisor: Advisor) -> None:
        """Update an existing advisor."""
        ...

