"""In-memory store for tracking background job statuses."""

from src.api.models.response import JobStatusResponse

# Global in-memory job storage
_jobs: dict[str, JobStatusResponse] = {}
