from dataclasses import dataclass
from typing import Any

from src.core.identifiers import EntityID
from src.domain.events.base import DomainEvent
from src.domain.value_objects.status import NotificationPriority, NotificationType


@dataclass(frozen=True)
class NotificationPushEvent(DomainEvent):
    user_id: EntityID
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority
    is_read: bool
    payload: dict[str, Any]
