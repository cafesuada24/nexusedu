"""Worker payloads for email tasks."""

from uuid import UUID

from src.application.dtos.worker_payloads.base import BaseWorkerPayload


class EmailDraftPayload(BaseWorkerPayload):
    """Payload for email draft generation task."""

    case_id: UUID


class DispatchEmailPayload(BaseWorkerPayload):
    """Payload for email dispatch task."""

    case_id: UUID


class DispatchReviewEmailPayload(BaseWorkerPayload):
    """Payload for review email dispatch task."""

    case_id: UUID
    header: str
    body: str
    target_email: str
