"""Worker payloads for gamification tasks."""

from datetime import datetime
from uuid import UUID

from src.domain.value_objects.student_satisfaction import StudentSatisfaction
from src.application.dtos.worker_payloads.base import BaseWorkerPayload


class EvaluateBadgesPayload(BaseWorkerPayload):
    """Payload for badge evaluation task."""

    advisor_id: UUID


class CaseAcceptedPayload(BaseWorkerPayload):
    """Payload for case accepted event handler."""

    case_id: UUID
    advisor_id: UUID
    occurred_at: datetime


class StudentBookedPayload(BaseWorkerPayload):
    """Payload for student booked event handler."""

    case_id: UUID
    occurred_at: datetime


class CaseResolvedPayload(BaseWorkerPayload):
    """Payload for case resolved event handler."""

    case_id: UUID
    advisor_id: UUID
    occurred_at: datetime
    satisfaction: StudentSatisfaction
    comment: str | None = None


class CaseFailedPayload(BaseWorkerPayload):
    """Payload for case failed event handler."""

    case_id: UUID
    advisor_id: UUID
    occurred_at: datetime
    satisfaction: str | None = None
    comment: str | None = None
