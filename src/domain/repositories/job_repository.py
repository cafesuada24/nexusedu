"""Job repository interface."""

from typing import Protocol
from uuid import UUID


class JobRepository(Protocol):
    """Interface for background job data operations."""

    async def create_job(
        self,
        job_id: UUID,
        job_type: str,
        correlation_id: UUID | None = None,
        correlation_type: str | None = None,
    ) -> None:
        """Record a new background job with optional correlation."""
        ...

    async def update_job_progress(
        self, job_id: UUID, progress: int, status_message: str | None = None
    ) -> None:
        """Update the progress and status message of a job."""
        ...

    async def start_job(self, job_id: UUID) -> None:
        """Mark a job as started."""
        ...

    async def complete_job(self, job_id: UUID) -> None:
        """Mark a background job as completed."""
        ...

    async def fail_job(self, job_id: UUID, error_message: str) -> None:
        """Mark a background job as failed."""
        ...

    async def get_active_job(
        self, correlation_id: UUID, correlation_type: str, job_type: str
    ) -> UUID | None:
        """Retrieve the active job ID for a specific correlation context."""
        ...

    async def batch_create_jobs(
        self, jobs: list[tuple[UUID, str, UUID | None, str | None]]
    ) -> None:
        """Batch record multiple background jobs."""
        ...
