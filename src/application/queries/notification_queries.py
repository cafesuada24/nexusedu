"""Query handlers for notification-related operations."""

import uuid

from src.domain.repositories.notification_repository import NotificationRepository
from src.presentation.schemas.notification import NotificationList, NotificationRead


class NotificationQueryHandler:
    """Handler for notification-related queries."""

    def __init__(self, notification_repo: NotificationRepository) -> None:
        """Initialize with a notification repository."""
        self._notification_repo = notification_repo

    async def list_notifications(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> NotificationList:
        """Retrieve a list of notifications for a specific user."""
        notifications = await self._notification_repo.list_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
        unread_count = await self._notification_repo.count_unread(user_id=user_id)

        # Domain entities are converted to Read schemas
        return NotificationList(
            notifications=[
                NotificationRead(
                    id=n.id,
                    type=n.type,
                    priority=n.priority,
                    title=n.title,
                    message=n.body,
                    payload=n.payload,
                    isRead=n.is_read,
                    timestamp=n.created_at,
                )
                for n in notifications
            ],
            unreadCount=unread_count,
        )
