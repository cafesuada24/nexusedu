"""Unit tests for the notification flow."""

import uuid
from datetime import UTC, datetime

from src.domain.entities.notification import Notification
from src.domain.events.notification_events import NotificationPushEvent
from src.domain.value_objects.status import NotificationPriority, NotificationType
from src.infrastructure.queue.outbox_mapper import OutboxMapper


def test_notification_registers_push_event():
    """Verify that Notification.create() registers a NotificationPushEvent."""
    user_id = uuid.uuid4()
    notification = Notification(
        user_id=user_id,
        type=NotificationType.INFO,
        title="Test Notification",
        body="This is a test notification.",
        priority=NotificationPriority.NORMAL,
        payload={"key": "value"}
    )
    
    notification.create()
    
    assert len(notification.domain_events) == 1
    event = notification.domain_events[0]
    assert isinstance(event, NotificationPushEvent)
    assert event.user_id == user_id
    assert event.type == NotificationType.INFO
    assert event.title == "Test Notification"
    assert event.message == "This is a test notification."
    assert event.payload == {"key": "value"}


def test_outbox_mapper_handles_notification_push_event():
    """Verify that OutboxMapper maps NotificationPushEvent to websocket_broadcast."""
    user_id = uuid.uuid4()
    event = NotificationPushEvent(
        user_id=user_id,
        type=NotificationType.SUCCESS,
        title="Success!",
        message="Operation completed.",
        priority=NotificationPriority.HIGH,
        occurred_at=datetime.now(UTC),
        is_read=False,
        payload={"op_id": "123"}
    )
    
    tasks = OutboxMapper.map_to_tasks(event)
    
    assert len(tasks) == 1
    task = tasks[0]
    assert task["task_name"] == "websocket_broadcast"
    assert task["kwargs"]["event_type"] == "NOTIFICATION:PUSH"
    assert task["kwargs"]["user_id"] == user_id
    assert task["kwargs"]["payload"]["title"] == "Success!"
    assert task["kwargs"]["payload"]["message"] == "Operation completed."
    assert task["kwargs"]["payload"]["type"] == NotificationType.SUCCESS
    assert "timestamp" in task["kwargs"]["payload"]
