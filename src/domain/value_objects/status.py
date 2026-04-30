"""Value objects for the domain."""

from enum import Enum


class RiskStatus(str, Enum):
    """Student risk status levels."""

    NORMAL = "Normal"
    ELEVATED = "Elevated"
    CRITICAL = "Critical"
    UNKNOWN = "Unknown"


class InterventionStatus(str, Enum):
    """Student intervention status levels."""

    NONE = "none"
    NOTIFIED = "notified"
    BOOKED = "booked"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class EmailStatus(str, Enum):
    """Status of an intervention email."""

    DRAFT = "draft"
    SENT = "sent"
