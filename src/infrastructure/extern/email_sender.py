"""Email sending implementation using aiosmtplib."""

from email.message import EmailMessage

import aiosmtplib
import structlog

logger = structlog.get_logger(__name__)


class AioSmtpEmailSender:
    """Implementation of EmailSendingService using aiosmtplib."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str | None = None,
        password: str | None = None,
        from_email: str = 'noreply@example.com',
    ) -> None:
        """Initialize the email sender with SMTP configuration."""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_email = from_email

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
    ) -> None:
        """Send an email using aiosmtplib."""
        logger.info(f'Sending email to {to_email} with subject: {subject}')

        message = EmailMessage()
        message['From'] = self.from_email
        message['To'] = to_email
        message['Subject'] = subject
        message.set_content(body)

        try:
            await aiosmtplib.send(
                message,
                use_tls=False,
                hostname=self.host or 'localhost',
                port=self.port,
                username=self.user,
                password=self.password,
            )
            logger.info(f'Email sent successfully to {to_email}')
        except Exception as e:
            logger.error(f'Failed to send email to {to_email}: {e}')
            raise
