"""Retry policy and exception classification for worker tasks."""

import asyncio
from dataclasses import dataclass
from typing import Any

from src.infrastructure.workers.framework.exceptions import (
    NonRetryableTaskError,
    RetryableTaskError,
    WorkerTaskError,
)


@dataclass(slots=True)
class RetryDecision:
    """Decision on whether to retry a task."""

    should_retry: bool
    reason: str | None = None
    retry_after: int | None = None


class RetryPolicy:
    """Policy for classifying exceptions and deciding on retries."""

    def classify(self, exc: Exception) -> RetryDecision:
        """Classify an exception and decide if it's retryable."""
        if isinstance(exc, asyncio.CancelledError):
            return RetryDecision(should_retry=False, reason="cancelled")

        if isinstance(exc, RetryableTaskError):
            return RetryDecision(should_retry=True, reason=str(exc))

        if isinstance(exc, NonRetryableTaskError):
            return RetryDecision(should_retry=False, reason=str(exc))

        if isinstance(exc, WorkerTaskError):
            return RetryDecision(should_retry=False, reason=str(exc))

        # Default: Unknown exceptions are considered non-retryable for safety
        # unless explicitly classified as retryable.
        # In a real system, you might want to retry on certain DB errors or timeouts.
        return RetryDecision(should_retry=False, reason=f"unhandled_exception: {type(exc).__name__}")


def map_exception_to_worker_error(exc: Exception, decision: RetryDecision) -> Exception:
    """Map a generic exception to a WorkerTaskError based on retry decision."""
    if isinstance(exc, (WorkerTaskError, asyncio.CancelledError)):
        return exc

    if decision.should_retry:
        return RetryableTaskError(decision.reason or str(exc))

    return NonRetryableTaskError(decision.reason or str(exc))
