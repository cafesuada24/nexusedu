"""Internal type definitions for the API."""

from src.api.models.response import JobStatusResponse
from src.utils.collections import BoundedDict

type JobStore = BoundedDict[str, JobStatusResponse]
