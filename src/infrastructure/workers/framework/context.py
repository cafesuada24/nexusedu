"""Worker task context management."""

from dataclasses import dataclass
from typing import Any

import structlog
from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.container import Container
from src.infrastructure.persistence.sqlalchemy_uow import SqlAlchemyUnitOfWork
from src.infrastructure.workers.framework.tracking import JobTracker


@dataclass(slots=True)
class TaskContext:
    """Context and dependencies for worker tasks."""

    session: AsyncSession
    container: Container
    uow: SqlAlchemyUnitOfWork
    logger: structlog.BoundLogger
    span: trace.Span
    job_tracker: JobTracker
    redis: Any | None = None
