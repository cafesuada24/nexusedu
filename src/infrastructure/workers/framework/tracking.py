"""Job tracking logic for worker tasks."""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from opentelemetry import trace

from src.infrastructure.persistence.sqlalchemy_uow import SqlAlchemyUnitOfWork

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


class JobTracker:
    """Encapsulates job state transitions for background jobs."""

    def __init__(
        self,
        uow: SqlAlchemyUnitOfWork,
        job_id: UUID | str | None = None,
        user_id: UUID | str | None = None,
    ) -> None:
        """Initialize with Unit of Work and optional job/user IDs."""
        self.uow = uow
        self.job_id = UUID(str(job_id)) if job_id else None
        self.user_id = UUID(str(user_id)) if user_id else None

    async def started(self) -> None:
        """Mark job as RUNNING."""
        if not self.job_id:
            return

        async with self.uow:
            job = await self.uow.jobs.get_by_id(self.job_id)
            if job:
                job.start(datetime.now(UTC), user_id=self.user_id)
                await self.uow.jobs.save(job)
                await self.uow.commit()

    async def finished(self) -> None:
        """Mark job as SUCCESS."""
        if not self.job_id:
            return

        async with self.uow:
            job = await self.uow.jobs.get_by_id(self.job_id)
            if job:
                job.finish(datetime.now(UTC), user_id=self.user_id)
                await self.uow.jobs.save(job)
                await self.uow.commit()

    async def failed(self) -> None:
        """Mark job as ERROR."""
        if not self.job_id:
            return

        try:
            async with self.uow:
                job = await self.uow.jobs.get_by_id(self.job_id)
                if job:
                    job.fail(datetime.now(UTC), user_id=self.user_id)
                    await self.uow.jobs.save(job)
                    await self.uow.commit()
        except Exception as e:
            logger.error(
                "failed_to_update_job_status_to_failed",
                job_id=str(self.job_id),
                error=str(e),
            )
