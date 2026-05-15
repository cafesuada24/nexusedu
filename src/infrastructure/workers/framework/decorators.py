"""Worker task decorators for cross-cutting concerns."""

import functools
from collections.abc import Awaitable, Callable
from typing import Any, Concatenate

import structlog
from opentelemetry import trace
from pydantic import BaseModel

from src.core.container import Container
from src.infrastructure.database.session import async_session_maker
from src.infrastructure.workers.framework.context import TaskContext
from src.infrastructure.workers.framework.middleware import (
    JobTrackingMiddleware,
    LoggingMiddleware,
    MiddlewarePipeline,
    RetryMiddleware,
    TracingMiddleware,
    TransactionMiddleware,
)
from src.infrastructure.workers.framework.tracking import JobTracker

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


def worker_task[**P, R](
    *,
    track_job: bool = False,
) -> Callable[
    [Callable[Concatenate[TaskContext, P], Awaitable[R]]],
    Callable[Concatenate[dict[str, Any], P], Awaitable[R]],
]:
    """Decorator for worker tasks using a middleware pipeline.

    - Database session and Unit of Work lifecycle
    - Dependency Injection (Container)
    - Structured logging with context
    - OpenTelemetry tracing
    - Automatic Job state updates (if track_job=True)
    - Exception handling and retry logic mapping
    """

    def decorator(
        func: Callable[Concatenate[TaskContext, P], Awaitable[R]],
    ) -> Callable[Concatenate[dict[str, Any], P], Awaitable[R]]:

        @functools.wraps(func)
        async def wrapper(
            arq_ctx: dict[str, Any],
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> R:
            # 1. Extract IDs for tracking
            job_id = kwargs.get('job_id')
            user_id = kwargs.get('user_id')

            if not job_id:
                # Check args for BaseModel payload
                for arg in args:
                    if isinstance(arg, BaseModel):
                        job_id = getattr(arg, 'job_id', None)
                        user_id = getattr(arg, 'user_id', None)
                        if job_id:
                            break

            if not job_id:
                # Check kwargs values (e.g. payload=BaseModel)
                for val in kwargs.values():
                    if isinstance(val, BaseModel):
                        job_id = getattr(val, 'job_id', None)
                        user_id = getattr(val, 'user_id', None)
                        if job_id:
                            break

            task_name = func.__name__
            log = logger.new(
                task=task_name,
                job_id=str(job_id) if job_id else None,
            )

            # 2. Build Context and Run Pipeline
            async with async_session_maker() as session:
                container = Container(session=session, redis_pool=arq_ctx.get('redis'))
                uow = container.uow

                job_tracker = JobTracker(uow=uow, job_id=job_id, user_id=user_id)

                # We start a span here to wrap the whole pipeline
                with tracer.start_as_current_span(f'worker.{task_name}') as span:
                    if job_id:
                        span.set_attribute('job_id', str(job_id))

                    ctx = TaskContext(
                        session=session,
                        container=container,
                        uow=uow,
                        logger=log,
                        span=span,
                        job_tracker=job_tracker,
                        redis=arq_ctx.get('redis'),
                    )

                    pipeline = MiddlewarePipeline(
                        [
                            TracingMiddleware(),
                            LoggingMiddleware(),
                            JobTrackingMiddleware(track_job=track_job),
                            RetryMiddleware(),
                            TransactionMiddleware(),
                        ],
                    )

                    return await pipeline.execute(
                        ctx,
                        lambda: func(ctx, *args, **kwargs),
                    )

        return wrapper

    return decorator
