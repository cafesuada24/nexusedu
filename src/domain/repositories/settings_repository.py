"""User settings repository interface."""

from typing import Protocol
from uuid import UUID


class UserSettingsRepository(Protocol):
    """Interface for user settings data operations."""

    async def get_auto_draft_enabled(self, user_id: UUID) -> bool:
        """Check if auto-drafting is enabled for a user."""
        ...

    async def update_auto_draft_enabled(self, user_id: UUID, enabled: bool) -> None:
        """Update the auto-drafting setting for a user."""
        ...
