"""Value objects for the domain."""

from enum import StrEnum


class RiskStatus(StrEnum):
    """Student risk status levels."""

    NORMAL = 'Normal'
    ELEVATED = 'Elevated'
    CRITICAL = 'Critical'
    UNKNOWN = 'Unknown'


class InterventionStatus(StrEnum):
    """Student intervention status levels."""

    NEW = 'new'
    ACCEPTED = 'accepted'
    SENT = 'sent'
    BOOKED = 'booked'
    SUPPORTING = 'supporting'
    PENDING_REVIEW = 'pending_review'
    RESOLVED = 'resolved'
    FAILED = 'failed'
    DISMISSED = 'dismissed'
    EXPIRED = 'expired'


class JobStatus(StrEnum):
    """Status of a background job."""

    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    ERROR = 'error'
    CANCELLED = 'cancelled'


class EmailStatus(StrEnum):
    """Status of an intervention email."""

    UNAVAILABLE = 'unavailable'
    GENERATING = 'generating'
    DRAFT = 'draft'
    SENT = 'sent'


class TaskStatus(StrEnum):
    """Status of a task."""

    AVAILABLE = 'available'
    BLOCKED = 'blocked'
    FAILED = 'failed'
    DONE = 'done'
