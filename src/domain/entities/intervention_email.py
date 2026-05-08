"""Intervention Email domain entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.exceptions import (
    EmptyEmailError,
    InvalidStateTransitionError,
)
from src.domain.value_objects.status import EmailStatus


@dataclass
class InterventionEmail:
    """Represents an intervention email drafted or sent to a student."""

    case_id: UUID
    status: EmailStatus = EmailStatus.UNAVAILABLE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    email_id: UUID = field(default_factory=uuid4)
    subject: str | None = None
    body: str | None = None
    sent_at: datetime | None = None

    @property
    def is_generating(self) -> bool:
        """Return if the email is generating."""
        return self.status == EmailStatus.GENERATING

    def set_draft_content(self, subject: str, body: str) -> None:
        """Called by the background worker when the AI is done."""
        if not subject.strip() or not body.strip():
            raise ValueError('Draft content cannot be empty')

        self.subject = subject
        self.body = body
        self.status = EmailStatus.DRAFT

    def mark_as_sent(self) -> None:
        """Mark this email as sent."""
        if self.status != EmailStatus.DRAFT:
            raise InvalidStateTransitionError(
                self.status.value,
                EmailStatus.SENT.value,
            )

        if not self.subject and not self.body:
            raise EmptyEmailError(self.case_id)

        self.status = EmailStatus.SENT
        self.sent_at = datetime.now(UTC)

    def mark_as_generating(self) -> None:
        """Mark this email as generating."""
        if self.status == EmailStatus.SENT:
            raise InvalidStateTransitionError(
                current_status=self.status.value,
                attempted_action=EmailStatus.GENERATING.value,
            )
        self.status = EmailStatus.GENERATING

    def prepare_for_regeneration(self) -> None:
        """Prepare for generate email."""
        self.status = EmailStatus.UNAVAILABLE
        self.subject = None
        self.body = None
        self.sent_at = None
