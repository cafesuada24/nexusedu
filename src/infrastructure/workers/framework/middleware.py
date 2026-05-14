"""Middleware pipeline for worker tasks."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypeVar

import structlog
from opentelemetry import trace

from src.infrastructure.workers.framework.context import TaskContext
from src.infrastructure.workers.framework.retry import (
    RetryPolicy,
    map_exception_to_worker_error,
)

T = TypeVar('T')
logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


class WorkerMiddleware(Protocol):
    """Protocol for worker task middleware."""

    async def __call__(
        self,
        ctx: TaskContext,
        next_call: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Execute middleware logic."""
        ...


class LoggingMiddleware:
    """Handles structured logging for worker tasks."""

    async def __call__(
        self,
        ctx: TaskContext,
        next_call: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Add context and log task execution."""
        ctx.logger.info('task_started')
        try:
            result = await next_call()
            ctx.logger.info('task_finished')
            return result
        except Exception as e:
            # We don't log error here because RetryMiddleware will handle it
            # and it has better visibility into the mapped exception.
            raise


class TracingMiddleware:
    """Handles OpenTelemetry tracing for worker tasks."""

    async def __call__(
        self,
        ctx: TaskContext,
        next_call: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Trace task execution."""
        with tracer.start_as_current_span(
            'worker_task',
            context=trace.set_span_in_context(ctx.span),
        ) as span:
            return await next_call()


class JobTrackingMiddleware:
    """Orchestrates job state updates."""

    def __init__(self, track_job: bool = False) -> None:
        """Initialize with tracking preference."""
        self.track_job = track_job

    async def __call__(
        self,
        ctx: TaskContext,
        next_call: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Update job status during execution."""
        if self.track_job:
            await ctx.job_tracker.started()

        try:
            result = await next_call()

            if self.track_job:
                await ctx.job_tracker.finished()

            return result
        except Exception:
            if self.track_job:
                await ctx.job_tracker.failed()
            raise


class RetryMiddleware:
    """Applies retry policy and maps exceptions."""

    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        """Initialize with optional retry policy."""
        self.retry_policy = retry_policy or RetryPolicy()

    async def __call__(
        self,
        ctx: TaskContext,
        next_call: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Apply retry logic."""
        try:
            return await next_call()
        except asyncio.CancelledError:
            ctx.logger.warning('task_cancelled')
            raise
        except Exception as e:
            decision = self.retry_policy.classify(e)

            if decision.should_retry:
                ctx.logger.warning(
                    'task_retryable_error',
                    error=str(e),
                    reason=decision.reason,
                    retry_after=decision.retry_after,
                )
            else:
                ctx.logger.error(
                    'task_failed',
                    error=str(e),
                    reason=decision.reason,
                    exc_info=True,
                )

            mapped_exc = map_exception_to_worker_error(e, decision)
            if mapped_exc is not e:
                raise mapped_exc from e
            raise mapped_exc from None


class TransactionMiddleware:
    """Manages the database session and UoW lifecycle."""

    async def __call__(
        self,
        ctx: TaskContext,
        next_call: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Ensure session is committed or rolled back."""
        try:
            result = await next_call()
            # We don't auto-commit here if the task is expected to manage its own UoW.
            # But the current implementation of SqlAlchemyUnitOfWork expects explicit commit.
            # Many tasks use 'async with deps.uow' which commits.
            # If the task doesn't use UoW, we might want to commit the session here
            # to persist any changes made directly to repositories.
            return result
        except Exception:
            await ctx.session.rollback()
            raise


class MiddlewarePipeline:
    """Executes a list of middlewares around a task."""

    def __init__(self, middlewares: list[WorkerMiddleware]) -> None:
        """Initialize with a list of middlewares."""
        self.middlewares = middlewares

    async def execute(
        self, ctx: TaskContext, task: Callable[[], Awaitable[Any]]
    ) -> Any:
        """Execute the pipeline."""

        async def _execute_recursive(index: int) -> Any:
            if index == len(self.middlewares):
                return await task()

            middleware = self.middlewares[index]
            return await middleware(ctx, lambda: _execute_recursive(index + 1))

        return await _execute_recursive(0)
