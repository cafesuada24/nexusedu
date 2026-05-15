"""Background job entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.core.identifiers import EntityID, generate_uuid
from src.domain.entities.base import AggregateRoot
from src.domain.events.job_events import JobStatusChangedEvent
from src.domain.exceptions import InvalidStateTransitionError
from src.domain.value_objects.status import JobStatus


@dataclass
class Job(AggregateRoot):
    """Background job."""

    correlation_id: EntityID
    correlation_type: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    job_id: EntityID = field(default_factory=generate_uuid)
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def start(self, occurred_at: datetime, user_id: EntityID | None = None) -> None:
        """Begin this job."""
        if self.status != JobStatus.PENDING:
            raise InvalidStateTransitionError(
                self.status.value,
                JobStatus.RUNNING,
            )
        self.status = JobStatus.RUNNING
        self.started_at = occurred_at
        self.register_event(
            JobStatusChangedEvent(
                job_id=self.job_id,
                status=self.status,
                correlation_id=self.correlation_id,
                correlation_type=self.correlation_type,
                user_id=user_id,
            ),
        )

    def finish(self, occurred_at: datetime, user_id: EntityID | None = None) -> None:
        """Finish this job."""
        if self.status != JobStatus.RUNNING:
            raise InvalidStateTransitionError(
                self.status.value,
                JobStatus.SUCCESS,
            )
        self.status = JobStatus.SUCCESS
        self.ended_at = occurred_at
        self.register_event(
            JobStatusChangedEvent(
                job_id=self.job_id,
                status=self.status,
                correlation_id=self.correlation_id,
                correlation_type=self.correlation_type,
                user_id=user_id,
            ),
        )

    def fail(self, occurred_at: datetime, user_id: EntityID | None = None) -> None:
        """Finish this job."""
        if self.status != JobStatus.RUNNING:
            raise InvalidStateTransitionError(
                self.status.value,
                JobStatus.ERROR,
            )
        self.status = JobStatus.ERROR
        self.ended_at = occurred_at
        self.register_event(
            JobStatusChangedEvent(
                job_id=self.job_id,
                status=self.status,
                correlation_id=self.correlation_id,
                correlation_type=self.correlation_type,
                user_id=user_id,
            )
        )

    def cancel(self, occurred_at: datetime) -> None:
        """Cancel this task."""
        if self.status not in (JobStatus.PENDING, JobStatus.RUNNING):
            raise InvalidStateTransitionError(
                self.status.value,
                JobStatus.CANCELLED,
            )
        self.status = JobStatus.CANCELLED
        self.ended_at = occurred_at
        self.register_event(
            JobStatusChangedEvent(
                job_id=self.job_id,
                status=self.status,
                correlation_id=self.correlation_id,
                correlation_type=self.correlation_type,
                user_id=None,
            )
        )
