"""Base worker payload classes."""

from uuid import UUID

from pydantic import BaseModel


class BaseWorkerPayload(BaseModel):
    """Base class for all worker task payloads."""

    job_id: UUID | None = None
    user_id: UUID | None = None
