"""Background job entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.core.identifiers import EntityID, generate_uuid
from src.domain.exceptions import InvalidStateTransitionError
from src.domain.value_objects.status import JobStatus


@dataclass
class Job:
    """Background job."""

    correlation_id: EntityID
    correlation_type: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    job_id: EntityID = field(default_factory=generate_uuid)
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def start(self, occurred_at: datetime) -> None:
        """Begin this job."""
        if self.status != JobStatus.PENDING:
            raise InvalidStateTransitionError(
                self.status.value,
                JobStatus.RUNNING,
            )
        self.status = JobStatus.RUNNING
        self.started_at = occurred_at

    def finish(self, occurred_at: datetime) -> None:
        """Finish this job."""
        if self.status != JobStatus.RUNNING:
            raise InvalidStateTransitionError(
                self.status.value,
                JobStatus.SUCCESS,
            )
        self.status = JobStatus.SUCCESS
        self.ended_at = occurred_at

    def fail(self, occurred_at: datetime) -> None:
        """Finish this job."""
        if self.status != JobStatus.RUNNING:
            raise InvalidStateTransitionError(
                self.status.value,
                JobStatus.ERROR,
            )
        self.status = JobStatus.ERROR
        self.ended_at = occurred_at

    def cancel(self, occurred_at: datetime) -> None:
        """Cancel this task."""
        if self.status in (JobStatus.PENDING, JobStatus.RUNNING):
            raise InvalidStateTransitionError(
                self.status.value,
                JobStatus.CANCELLED,
            )
        self.status = JobStatus.CANCELLED
        self.ended_at = occurred_at
