"""Schemas for notification-related requests and responses."""

from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field

from src.domain.value_objects.status import NotificationPriority, NotificationType


class NotificationRead(BaseModel):
    """Schema for reading a notification."""

    id: UUID
    type: NotificationType
    priority: NotificationPriority
    title: str
    body: str = Field(..., alias='message')
    payload: dict[str, Any]
    is_read: bool = Field(..., alias='isRead')
    created_at: AwareDatetime = Field(..., alias='timestamp')

    model_config = {
        'populate_by_name': True,
    }


class NotificationList(BaseModel):
    """Schema for a list of notifications."""

    notifications: list[NotificationRead]
    unread_count: int = Field(..., alias='unreadCount')

    model_config = {
        'populate_by_name': True,
    }
