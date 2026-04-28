"""Internal type definitions for the API."""

from src.api.models.response import JobStatusResponse
from src.types import BoundedDict

type JobStore = BoundedDict[str, JobStatusResponse]
