import pytest
from unittest.mock import AsyncMock, patch
from email.message import EmailMessage
from src.infrastructure.extern.email_sender import AioSmtpEmailSender

@pytest.mark.asyncio
async def test_aio_smtp_email_sender_parameters():
    """Verify that AioSmtpEmailSender passes correct parameters to aiosmtplib."""
    sender = AioSmtpEmailSender(
        host='smtp.mailgun.org',
        port=587,
        user='user',
        password='password',
        from_email='noreply@test.com',
        use_tls=False,
        start_tls=True
    )

    with patch('aiosmtplib.send', new_callable=AsyncMock) as mock_send:
        await sender.send_email(
            to_email='student@test.com',
            subject='Test Subject',
            body='Test Body',
            reply_to='advisor@test.com'
        )

        # Verify aiosmtplib.send call
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        
        # Check message headers
        message = args[0]
        assert isinstance(message, EmailMessage)
        assert message['From'] == 'noreply@test.com'
        assert message['To'] == 'student@test.com'
        assert message['Subject'] == 'Test Subject'
        assert message['Reply-To'] == 'advisor@test.com'
        
        # Check security parameters
        assert kwargs['hostname'] == 'smtp.mailgun.org'
        assert kwargs['port'] == 587
        assert kwargs['username'] == 'user'
        assert kwargs['password'] == 'password'
        assert kwargs['use_tls'] is False
        assert kwargs['start_tls'] is True

@pytest.mark.asyncio
async def test_aio_smtp_email_sender_no_reply_to():
    """Verify that Reply-To is omitted when not provided."""
    sender = AioSmtpEmailSender(
        host='localhost',
        port=1025,
        from_email='noreply@test.com'
    )

    with patch('aiosmtplib.send', new_callable=AsyncMock) as mock_send:
        await sender.send_email(
            to_email='student@test.com',
            subject='Test Subject',
            body='Test Body'
        )

        message = mock_send.call_args[0][0]
        assert 'Reply-To' not in message
