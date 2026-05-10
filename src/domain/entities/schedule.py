"""Advisor schedule domain entities."""

from dataclasses import dataclass, field
from datetime import date, time
from uuid import UUID, uuid4


@dataclass
class WorkingHours:
    """Represents a recurring weekly working hour block for an advisor."""

    advisor_id: UUID
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: time
    end_time: time
    timezone: str = 'UTC'
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        """Validate working hours invariants."""
        if not (0 <= self.day_of_week <= 6):
            raise ValueError('day_of_week must be between 0 and 6')
        if self.start_time >= self.end_time:
            raise ValueError('start_time must be before end_time')

    def update(
        self,
        day_of_week: int,
        start_time: time,
        end_time: time,
        timezone: str,
    ) -> None:
        """Update working hours properties and re-validate invariants."""
        self.day_of_week = day_of_week
        self.start_time = start_time
        self.end_time = end_time
        self.timezone = timezone
        self.__post_init__()


@dataclass
class DayOff:
    """Represents a specific date when an advisor is unavailable."""

    advisor_id: UUID
    date: date
    reason: str | None = None
    id: UUID = field(default_factory=uuid4)
