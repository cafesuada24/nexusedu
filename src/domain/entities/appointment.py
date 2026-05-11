"""Appointment domain entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.core.identifiers import EntityID, generate_uuid
from src.domain.value_objects.status import MeetingMethod


@dataclass
class Appointment:
    """Represents a scheduled meeting between a student and an advisor."""

    case_id: EntityID
    appointment_time: datetime
    meeting_method: MeetingMethod
    duration_minutes: int = 30
    notes: str | None = None
    appointment_id: EntityID = field(default_factory=generate_uuid)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate appointment invariants."""
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
