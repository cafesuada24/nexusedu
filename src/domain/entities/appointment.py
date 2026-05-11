"""Appointment domain entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

import uuid6

from src.domain.value_objects.status import MeetingMethod


@dataclass
class Appointment:
    """Represents a scheduled meeting between a student and an advisor."""

    case_id: UUID
    appointment_time: datetime
    meeting_method: MeetingMethod
    notes: str | None = None
    appointment_id: UUID = field(default_factory=uuid6.uuid7)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
