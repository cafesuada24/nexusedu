"""Job repository interface."""

from typing import Protocol

from src.core.identifiers import EntityID
from src.domain.entities.job import Job


class JobRepository(Protocol):
    """Interface for background job data operations."""

    async def add(self, job: Job) -> None:
        """Record an background job."""
        ...

    async def get_by_id(self, job_id: EntityID) -> Job:
        """Get a job by id."""
        ...

    async def find_by_correlation_id(
        self,
        correlation_id: EntityID,
        correlation_type: str,
    ) -> Job | None:
        """Find job by a correlation id."""
        ...

    async def get_by_correlation_id(
        self,
        correlation_id: EntityID,
        correlation_type: str,
    ) -> Job:
        """Find job by a correlation id."""
        ...

    async def save(self, job: Job) -> None:
        """Update an existing job."""
        ...
