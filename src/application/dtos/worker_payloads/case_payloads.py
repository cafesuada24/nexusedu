"""Worker payloads for case-related tasks."""

from datetime import datetime
from uuid import UUID

from src.application.dtos.worker_payloads.base import BaseWorkerPayload


class CaseReviewRequestedPayload(BaseWorkerPayload):
    """Payload for case review requested event handler."""

    case_id: UUID
    advisor_id: UUID
    occurred_at: datetime


class AutoResolveCasePayload(BaseWorkerPayload):
    """Payload for auto-resolve case task."""

    case_id: UUID


class AdvisorCreatedPayload(BaseWorkerPayload):
    """Payload for advisor created event handler."""

    advisor_id: UUID
    email: str
    name: str
    occurred_at: datetime
