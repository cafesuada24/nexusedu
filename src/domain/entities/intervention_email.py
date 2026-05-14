"""Intervention Email domain entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.core.identifiers import EntityID, generate_uuid
from src.domain.entities.base import AggregateRoot
from src.domain.exceptions import (
    EmptyEmailError,
    InvalidActionError,
    InvalidStateTransitionError,
)
from src.domain.value_objects.status import EmailStatus


@dataclass
class InterventionEmail(AggregateRoot):
    """Represents an intervention email drafted or sent to a student."""

    case_id: EntityID
    status: EmailStatus = EmailStatus.UNAVAILABLE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    email_id: EntityID = field(default_factory=generate_uuid)
    subject: str | None = None
    body: str | None = None
    sent_at: datetime | None = None
    version: int = 0

    @property
    def is_generating(self) -> bool:
        """Return if the email is generating."""
        return self.status == EmailStatus.GENERATING

    @property
    def is_ready_to_send(self) -> bool:
        """Return if the email is generating."""
        return self.status == EmailStatus.DRAFT

    def set_draft_content(self, subject: str, body: str) -> None:
        """Called by the background worker when the AI is done."""
        if self.status != EmailStatus.GENERATING:
            raise InvalidActionError('The email is not generating, cannot update.')
        if not subject.strip() or not body.strip():
            raise ValueError('Draft content cannot be empty')

        self.subject = subject
        self.body = body
        self.status = EmailStatus.DRAFT

    def update_draft(self, subject: str, body: str) -> None:
        """Manually update the draft content by an advisor."""
        if self.status not in (EmailStatus.DRAFT, EmailStatus.UNAVAILABLE):
            raise InvalidActionError(
                f'Cannot update draft as the email is {self.status}',
            )

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
