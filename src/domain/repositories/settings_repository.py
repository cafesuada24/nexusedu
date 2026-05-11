"""User settings repository interface."""

from typing import Protocol

from src.core.identifiers import EntityID


class UserSettingsRepository(Protocol):
    """Interface for user settings data operations."""

    async def get_auto_draft_enabled(self, user_id: EntityID) -> bool:
        """Check if auto-drafting is enabled for a user."""
        ...

    async def update_auto_draft_enabled(self, user_id: EntityID, enabled: bool) -> None:
        """Update the auto-drafting setting for a user."""
        ...

    async def create_user_settings(self, user_id: EntityID) -> None:
        """Create a new user settings."""
        ...
