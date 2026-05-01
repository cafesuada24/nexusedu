"""Interface for background task queueing."""

from typing import Any, Protocol


class BackgroundTaskQueue(Protocol):
    """Port for background task execution."""

    async def enqueue(self, task_name: str, **kwargs: Any) -> Any:  # noqa: ANN401
        """Enqueue a task for background execution."""
        ...

    async def is_available(self) -> bool:
        """Check if the background queue is available and healthy."""
        ...
