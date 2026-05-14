"""Mapper for domain events to outbox tasks."""

from typing import Any

from src.application.dtos.worker_payloads.case_payloads import (
    AdvisorCreatedPayload,
    CaseReviewRequestedPayload,
)
from src.application.dtos.worker_payloads.email_payloads import (
    DispatchEmailPayload,
    EmailDraftPayload,
)
from src.application.dtos.worker_payloads.gamification_payloads import (
    CaseAcceptedPayload,
    CaseFailedPayload,
    CaseResolvedPayload,
    StudentBookedPayload,
)
from src.domain.events.advisor_events import AdvisorCreatedEvent
from src.domain.events.base import DomainEvent
from src.domain.events.case_events import (
    CaseAcceptedEvent,
    CaseFailedEvent,
    CaseResolvedEvent,
    CaseReviewRequestedEvent,
    EmailDraftRequestedEvent,
    InterventionEmailSentEvent,
    StudentBookedEvent,
)
from src.domain.events.job_events import JobStatusChangedEvent
from src.domain.value_objects.status import JobStatus


class OutboxMapper:
    """Centralized mapping of domain events to background and websocket tasks."""

    @staticmethod
    def map_to_tasks(event: DomainEvent) -> list[dict[str, Any]]:
        """Map a single domain event to one or more outbox tasks.

        Each dictionary in the returned list contains:
        - task_name: The name of the background task to execute.
        - kwargs: The arguments for the task.
        """
        tasks: list[dict[str, Any]] = []

        # Background Tasks (Existing logic from TaskQueueEventPublisher)
        bg_task = OutboxMapper._map_to_background_task(event)
        if bg_task:
            tasks.append(bg_task)

        # WebSocket Tasks
        ws_task = OutboxMapper._map_to_websocket_task(event)
        if ws_task:
            tasks.append(ws_task)

        return tasks

    @staticmethod
    def _map_to_background_task(event: DomainEvent) -> dict[str, Any] | None:
        """Map a domain event to a standard background worker task."""
        if isinstance(event, CaseAcceptedEvent):
            return {
                'task_name': 'run_case_accepted_task',
                'kwargs': {
                    'payload': CaseAcceptedPayload(
                        case_id=event.case_id,
                        advisor_id=event.advisor_id,
                        occurred_at=event.occurred_at,
                    ),
                },
            }
        if isinstance(event, EmailDraftRequestedEvent):
            return {
                'task_name': 'run_email_draft_task',
                'kwargs': {
                    'payload': EmailDraftPayload(
                        case_id=event.case_id,
                        job_id=event.job_id,
                        user_id=event.user_id,
                    ),
                },
            }
        if isinstance(event, InterventionEmailSentEvent):
            return {
                'task_name': 'run_dispatch_email_task',
                'kwargs': {
                    'payload': DispatchEmailPayload(
                        case_id=event.case_id,
                        job_id=event.job_id,
                        user_id=event.user_id,
                    ),
                },
            }
        if isinstance(event, StudentBookedEvent):
            return {
                'task_name': 'run_student_booked_task',
                'kwargs': {
                    'payload': StudentBookedPayload(
                        case_id=event.case_id,
                        occurred_at=event.occurred_at,
                    ),
                },
            }
        if isinstance(event, AdvisorCreatedEvent):
            return {
                'task_name': 'run_advisor_created_task',
                'kwargs': {
                    'payload': AdvisorCreatedPayload(
                        advisor_id=event.advisor_id,
                        email=event.email,
                        name=event.name,
                        occurred_at=event.occurred_at,
                    ),
                },
            }
        if isinstance(event, CaseResolvedEvent):
            return {
                'task_name': 'run_case_resolved_task',
                'kwargs': {
                    'payload': CaseResolvedPayload(
                        case_id=event.case_id,
                        advisor_id=event.advisor_id,
                        occurred_at=event.occurred_at,
                        satisfaction=event.satisfaction,
                        comment=event.comment,
                    ),
                },
            }
        if isinstance(event, CaseFailedEvent):
            return {
                'task_name': 'run_case_failed_task',
                'kwargs': {
                    'payload': CaseFailedPayload(
                        case_id=event.case_id,
                        advisor_id=event.advisor_id,
                        occurred_at=event.occurred_at,
                        satisfaction=event.satisfaction,
                        comment=event.comment,
                    ),
                },
            }
        if isinstance(event, CaseReviewRequestedEvent):
            return {
                'task_name': 'run_case_review_requested_task',
                'kwargs': {
                    'payload': CaseReviewRequestedPayload(
                        case_id=event.case_id,
                        advisor_id=event.advisor_id,
                        occurred_at=event.occurred_at,
                    ),
                },
            }
        return None

    @staticmethod
    def _map_to_websocket_task(event: DomainEvent) -> dict[str, Any] | None:
        """Map a domain event to a WebSocket broadcast task."""
        if isinstance(event, JobStatusChangedEvent):
            status_to_type = {
                JobStatus.RUNNING: 'JOB:STARTED',
                JobStatus.SUCCESS: 'JOB:COMPLETED',
                JobStatus.ERROR: 'JOB:FAILED',
                JobStatus.CANCELLED: 'JOB:CANCELLED',
            }
            event_type = status_to_type.get(
                event.status,
                f'JOB:{event.status.value.upper()}',
            )

            return {
                'task_name': 'websocket_broadcast',
                'kwargs': {
                    'event_type': event_type,
                    'payload': {
                        'job_id': str(event.job_id),
                        'status': event.status.value,
                        'correlation_id': str(event.correlation_id),
                        'correlation_type': event.correlation_type,
                    },
                    'user_id': event.user_id,
                },
            }

        # Generic pattern for CASE:STATUS_UPDATED notifications
        case_events = (
            CaseAcceptedEvent,
            InterventionEmailSentEvent,
            StudentBookedEvent,
            CaseResolvedEvent,
            CaseFailedEvent,
            CaseReviewRequestedEvent,
        )

        if isinstance(event, case_events):
            status_map = {
                CaseAcceptedEvent: 'ACCEPTED',
                InterventionEmailSentEvent: 'SENT',
                StudentBookedEvent: 'BOOKED',
                CaseResolvedEvent: 'RESOLVED',
                CaseFailedEvent: 'FAILED',
                CaseReviewRequestedEvent: 'PENDING_REVIEW',
            }

            payload = {
                'case_id': str(event.case_id),
                'new_status': status_map[type(event)],
            }

            # Optional advisor context
            user_id = None
            if hasattr(event, 'advisor_id'):
                user_id = event.advisor_id
            elif hasattr(event, 'user_id'):
                user_id = event.user_id

            # Appointment specifics
            if isinstance(event, StudentBookedEvent):
                payload['appointment'] = {
                    'appointment_time': event.appointment_time.isoformat(),
                    'meeting_method': event.meeting_method.value,
                    'notes': event.notes,
                }

            return {
                'task_name': 'websocket_broadcast',
                'kwargs': {
                    'event_type': 'CASE:STATUS_UPDATED',
                    'payload': payload,
                    'user_id': user_id,
                },
            }

        return None
