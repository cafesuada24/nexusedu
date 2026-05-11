"""Concrete implementation of EventPublisher using a background task queue."""

from collections.abc import Sequence

from src.application.interfaces.background_queue import BackgroundTaskQueue
from src.domain.events.advisor_events import AdvisorCreatedEvent
from src.domain.events.base import DomainEvent
from src.domain.events.case_events import (
    CaseAcceptedEvent,
    CaseFailedEvent,
    CaseResolvedEvent,
    CaseReviewRequestedEvent,
    StudentBookedEvent,
)


class TaskQueueEventPublisher:
    """Dispatches domain events to background tasks."""

    def __init__(self, task_queue: BackgroundTaskQueue) -> None:
        """Initialize with a task queue."""
        self.task_queue = task_queue

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        """Publish events by routing them to background tasks."""
        for event in events:
            if isinstance(event, CaseAcceptedEvent):
                await self.task_queue.enqueue(
                    'run_case_accepted_task',
                    case_id=event.case_id,
                    advisor_id=event.advisor_id,
                    occurred_at=event.occurred_at,
                )
            elif isinstance(event, StudentBookedEvent):
                await self.task_queue.enqueue(
                    'run_student_booked_task',
                    case_id=event.case_id,
                    occurred_at=event.occurred_at,
                )
            elif isinstance(event, AdvisorCreatedEvent):
                await self.task_queue.enqueue(
                    'run_advisor_created_task',
                    advisor_id=event.advisor_id,
                    email=event.email,
                    name=event.name,
                    occurred_at=event.occurred_at,
                )
            elif isinstance(event, CaseResolvedEvent):
                await self.task_queue.enqueue(
                    'run_case_resolved_task',
                    case_id=event.case_id,
                    advisor_id=event.advisor_id,
                    occurred_at=event.occurred_at,
                    satisfaction=event.satisfaction,
                    comment=event.comment,
                )
            elif isinstance(event, CaseFailedEvent):
                await self.task_queue.enqueue(
                    'run_case_failed_task',
                    case_id=event.case_id,
                    advisor_id=event.advisor_id,
                    occurred_at=event.occurred_at,
                    satisfaction=event.satisfaction,
                    comment=event.comment,
                )
            elif isinstance(event, CaseReviewRequestedEvent):
                await self.task_queue.enqueue(
                    'run_case_review_requested_task',
                    case_id=event.case_id,
                    advisor_id=event.advisor_id,
                    occurred_at=event.occurred_at,
                )
