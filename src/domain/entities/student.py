"""Student domain entity."""

from dataclasses import dataclass
from datetime import datetime

from src.core.identifiers import EntityID
from src.domain.value_objects.status import RiskStatus


@dataclass
class Student:
    """Represents a student in the system."""

    sid: EntityID
    student_name: str
    email: str
    major: str
    last_notified_timestamp: datetime | None
    current_risk_status: RiskStatus
    last_notified_satisfaction: int | None

    def update_risk(self, status: RiskStatus) -> None:
        """Update the student's risk status."""
        self.current_risk_status = status
