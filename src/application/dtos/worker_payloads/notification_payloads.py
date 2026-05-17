"""Worker payloads for notification-related tasks."""

from datetime import datetime
from typing import Any
from uuid import UUID

from src.application.dtos.worker_payloads.base import BaseWorkerPayload
from src.domain.value_objects.status import NotificationPriority, NotificationType


class CreateNotificationPayload(BaseWorkerPayload):
    """Payload for creating a persistent notification."""

    user_id: UUID | None = None
    advisor_id: UUID | None = None
    case_id: UUID | None = None
    type: NotificationType
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    payload: dict[str, Any] | None = None
    occurred_at: datetime


class NotificationPushPayload(BaseWorkerPayload):
    """Payload for WebSocket notification broadcast."""

    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority
    payload: dict[str, Any]
    timestamp: datetime

