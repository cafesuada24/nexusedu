"""Data Transfer Objects for the Application layer."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.domain.value_objects.status import InterventionStatus, RiskStatus


@dataclass
class StudentDTO:
    """DTO for student data."""

    sid: str
    name: Optional[str]
    email: Optional[str]
    major: str
    current_risk_status: RiskStatus
    intervention_status: InterventionStatus
    last_notified_timestamp: float


@dataclass
class AlertDTO:
    """DTO for alert data."""

    student: StudentDTO
    alert_details: Dict[str, Any]


@dataclass
class EmailDTO:
    """DTO for intervention email data."""

    email_id: str
    sid: str
    subject: Optional[str]
    body: Optional[str]
    status: str
    created_at: str
    sent_at: Optional[str] = None
