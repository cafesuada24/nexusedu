"""Intervention Email domain entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.value_objects.status import EmailStatus


@dataclass
class InterventionEmail:
    """Represents an intervention email drafted or sent to a student."""

    email_id: UUID
    advisor_id: UUID | None
    subject: str | None
    body: str | None
    created_at: datetime
    sent_at: datetime | None
    status: EmailStatus
    sid: UUID
    case_id: UUID | None = None
