"""Student domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.domain.value_objects.status import InterventionStatus, RiskStatus


@dataclass
class Student:
    """Represents a student in the system."""

    sid: str
    name: Optional[str] = None
    email: Optional[str] = None
    major: str = "Unknown"
    current_risk_status: RiskStatus = RiskStatus.NORMAL
    intervention_status: InterventionStatus = InterventionStatus.NONE
    last_notified_timestamp: float = 0.0
    last_notified_satisfaction: int = 0
    draft_job_id: Optional[str] = None

    def update_risk(self, status: RiskStatus) -> None:
        """Update the student's risk status."""
        self.current_risk_status = status

    def update_intervention(self, status: InterventionStatus) -> None:
        """Update the student's intervention status."""
        self.intervention_status = status
