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
        use_tls: bool = False,
        start_tls: bool = False,
    ) -> None:
        """Initialize the email sender with SMTP configuration."""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls
        self.start_tls = start_tls

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
    ) -> None:
        """Send an email using aiosmtplib."""
        logger.info(
            'Sending email',
            to_email=to_email,
            subject=subject,
            reply_to=reply_to,
        )

        message = EmailMessage()
        message['From'] = self.from_email
        message['To'] = to_email
        message['Subject'] = subject
        if reply_to:
            message['Reply-To'] = reply_to
        message.set_content(body)

        try:
            await aiosmtplib.send(
                message,
                hostname=self.host or 'localhost',
                port=self.port,
                username=self.user,
                password=self.password,
                use_tls=self.use_tls,
                start_tls=self.start_tls,
            )
            logger.info('Email sent successfully', to_email=to_email)
        except Exception as e:
            logger.error(
                'Failed to send email',
                to_email=to_email,
                error=str(e),
            )
            raise
