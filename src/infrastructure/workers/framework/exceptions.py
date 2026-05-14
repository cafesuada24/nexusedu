"""Worker-specific exceptions for retry logic."""


class WorkerTaskError(Exception):
    """Base exception for all worker task errors."""


class RetryableTaskError(WorkerTaskError):
    """Exception indicating that the task should be retried."""


class NonRetryableTaskError(WorkerTaskError):
    """Exception indicating that the task should NOT be retried."""
