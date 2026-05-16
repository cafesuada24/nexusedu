"""Implementation of the background queue using ARQ and Redis."""

from typing import Any

from arq import ArqRedis

from src.application.interfaces.background_queue import BackgroundTaskQueue


class ArqTaskQueueAdapter(BackgroundTaskQueue):
    """Adapter for the ARQ Redis pool."""

    def __init__(self, arq_pool: ArqRedis) -> None:
        """Initialize the adapter with an ARQ pool."""
        self.arq_pool = arq_pool

    async def enqueue(
        self,
        task_name: str,
        _job_id: str | None = None,
        **kwargs: Any,
    ) -> Any:  # noqa: ANN401
        """Enqueue a task into the ARQ pool."""
        return await self.arq_pool.enqueue_job(task_name, _job_id=_job_id, **kwargs)

    async def is_available(self) -> bool:
        """Check if Redis is reachable."""
        try:
            return await self.arq_pool.all_job_results() is not None
        except Exception:
            return False
