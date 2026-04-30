"""Alert domain entity."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.domain.entities.student import Student


@dataclass
class Alert:
    """Represents an active alert for a student."""

    student: Student
    alert_details: Dict[str, Any]
    created_at: Optional[float] = None
