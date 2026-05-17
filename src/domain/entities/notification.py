"""Notification domain entity."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.core.identifiers import EntityID, generate_uuid
from src.domain.entities.base import AggregateRoot
from src.domain.events.notification_events import NotificationPushEvent
from src.domain.value_objects.status import NotificationPriority, NotificationType


@dataclass
class Notification(AggregateRoot):
    """Represents a user notification."""

    user_id: EntityID
    type: NotificationType
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    payload: dict[str, Any] = field(default_factory=dict[str, Any])
    is_read: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: EntityID = field(default_factory=generate_uuid)

    def create(self) -> None:
        self.register_event(
            NotificationPushEvent(
                user_id=self.user_id,
                type=self.type,
                title=self.title,
                message=self.body,
                priority=self.priority,
                is_read=self.is_read,
                payload=self.payload,
                occurred_at=self.created_at,
            ),
        )
