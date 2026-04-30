"""Intervention Email domain entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.value_objects.status import EmailStatus


@dataclass
class InterventionEmail:
    """Represents an intervention email drafted or sent to a student."""

    email_id: str
    sid: str
    advisor_id: Optional[str]
    subject: Optional[str]
    body: Optional[str]
    status: EmailStatus
    created_at: datetime
    sent_at: Optional[datetime] = None
