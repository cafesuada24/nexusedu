"""Notification repository interface."""

from typing import Protocol

from src.core.identifiers import EntityID
from src.domain.entities.notification import Notification


class NotificationRepository(Protocol):
    """Interface for notification-related data operations."""

    async def add(self, notification: Notification) -> None:
        """Save a new notification."""
        ...

    async def get_by_id(self, notification_id: EntityID) -> Notification | None:
        """Find a notification by its ID."""
        ...

    async def list_by_user(
        self,
        user_id: EntityID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Notification]:
        """List notifications for a specific user, sorted by creation date."""
        ...

    async def mark_as_read(self, notification_id: EntityID) -> None:
        """Mark a notification as read."""
        ...

    async def mark_all_as_read(self, user_id: EntityID) -> None:
        """Mark all notifications for a user as read."""
        ...

    async def count_unread(self, user_id: EntityID) -> int:
        """Count unread notifications for a user."""
        ...
