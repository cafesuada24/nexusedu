"""Worker payloads for AI-related tasks."""

from uuid import UUID

from src.application.dtos.worker_payloads.base import BaseWorkerPayload


class GenerateCaseOverviewPayload(BaseWorkerPayload):
    """Payload for generating AI overview for a single case."""

    case_id: UUID
