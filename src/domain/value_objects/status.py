"""Value objects for the domain."""

from enum import StrEnum


class RiskStatus(StrEnum):
    """Student risk status levels."""

    NORMAL = "Normal"
    ELEVATED = "Elevated"
    CRITICAL = "Critical"
    UNKNOWN = "Unknown"


class InterventionStatus(StrEnum):
    """Student intervention status levels."""

    NONE = "none"
    NOTIFIED = "notified"
    BOOKED = "booked"
    SENT = "sent"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class EmailStatus(StrEnum):
    """Status of an intervention email."""

    DRAFT = "draft"
    SENT = "sent"
