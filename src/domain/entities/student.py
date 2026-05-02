"""Student domain entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.value_objects.status import InterventionStatus, RiskStatus


@dataclass
class Student:
    """Represents a student in the system."""

    sid: UUID
    student_name: str | None
    email: str | None
    major: str
    last_notified_timestamp: datetime | None
    current_risk_status: RiskStatus
    intervention_status: InterventionStatus
    last_notified_satisfaction: int = 0

    def update_risk(self, status: RiskStatus) -> None:
        """Update the student's risk status."""
        self.current_risk_status = status

    def update_intervention(self, status: InterventionStatus) -> None:
        """Update the student's intervention status."""
        self.intervention_status = status
