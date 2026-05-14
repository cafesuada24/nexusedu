"""Background job domain events."""

from dataclasses import dataclass

from src.core.identifiers import EntityID
from src.domain.events.base import DomainEvent
from src.domain.value_objects.status import JobStatus


@dataclass(frozen=True)
class JobStatusChangedEvent(DomainEvent):
    """Event triggered when a background job status changes."""

    job_id: EntityID
    status: JobStatus
    correlation_id: EntityID
    correlation_type: str
    user_id: EntityID | None = None
