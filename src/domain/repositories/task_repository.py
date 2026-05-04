"""Task repository interface."""

from typing import Protocol
from uuid import UUID

from src.domain.entities.task import Task


class TaskRepository(Protocol):
    """Interface for managing tasks associated with cases."""

    async def create_task(self, task: Task) -> None:
        """Create a new task."""
        ...

    async def get_by_id(self, task_id: UUID) -> Task | None:
        """Retrieve a task by its ID."""
        ...

    async def get_by_case(self, case_id: UUID) -> list[Task]:
        """Retrieve all tasks for a specific case."""
        ...

    async def update_task(self, task: Task) -> None:
        """Update an existing task."""
        ...
