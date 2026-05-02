"""Job repository interface."""

from typing import Protocol
from uuid import UUID


class JobRepository(Protocol):
    """Interface for background job data operations."""

    async def create_job(self, job_id: UUID, sid: UUID, job_type: str) -> None:
        """Record a new background job."""
        ...

    async def get_active_job(self, sid: UUID, job_type: str) -> UUID | None:
        """Retrieve the active job ID for a student and job type, if any."""
        ...

    async def complete_job(self, job_id: UUID) -> None:
        """Mark a background job as completed (or remove it)."""
        ...

    async def batch_create_jobs(self, jobs: list[tuple[UUID, UUID, str]]) -> None:
        """Batch record multiple background jobs.
        
        Args:
            jobs: List of (job_id, sid, job_type) tuples.
        """
        ...
