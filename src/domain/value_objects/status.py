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
    SUPPORTING = "supporting"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class CaseStatus(StrEnum):
    """Status of a student case."""

    OPEN = "open"
    RESOLVED = "resolved"
    CLOSED = "closed"


class EmailStatus(StrEnum):
    """Status of an intervention email."""

    GENERATING = "generating"
    DRAFT = "draft"
    SENT = "sent"
