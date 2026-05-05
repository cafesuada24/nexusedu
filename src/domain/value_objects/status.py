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
    ASSIGNED = "assigned"
    RESOLVED = "resolved"
    FAILED = "failed"


class TaskStatus(StrEnum):
    """Status of a task."""

    PENDING = "pending"
    COMPLETED = "completed"


class TaskType(StrEnum):
    """Types of tasks that can be performed on a case."""

    SEND_EMAIL = "send email"
    STUDENT_BOOK = "student book"
    RESOLVE_CASE = "resolve case"
    REVIEW_DRAFT = "review draft"


class EmailStatus(StrEnum):
    """Status of an intervention email."""

    GENERATING = "generating"
    DRAFT = "draft"
    SENT = "sent"

