"""Alert domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.entities.student import Student


@dataclass
class Alert:
    """Represents an active alert for a student."""

    id: UUID # Use student id
    student: Student
    created_at: datetime
    alert_details: dict[str, Any] = field(default_factory=dict[str, Any])
