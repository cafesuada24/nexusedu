"""Domain service for sending emails."""
from typing import Protocol


class EmailSendingService(Protocol):
    """Domain service for sending emails."""

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
    ) -> None:
        """Send an email to a recipient."""
        ...
