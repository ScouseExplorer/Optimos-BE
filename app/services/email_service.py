"""Email service for sending verification and password reset emails."""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


# Email Templates
VERIFICATION_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .button { background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }
        .footer { color: #666; font-size: 12px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Welcome to {{ app_name }}!</h2>
        <p>Thank you for signing up. Please verify your email address by clicking the button below:</p>
        <p>
            <a href="{{ verification_link }}" class="button">Verify Email</a>
        </p>
        <p>Or copy and paste this link in your browser:</p>
        <p><code>{{ verification_link }}</code></p>
        <p>This link expires in 24 hours.</p>
        <div class="footer">
            <p>If you didn't sign up for {{ app_name }}, you can ignore this email.</p>
        </div>
    </div>
</body>
</html>
"""

PASSWORD_RESET_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .button { background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }
        .footer { color: #666; font-size: 12px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Password Reset Request</h2>
        <p>We received a request to reset your password. Click the button below to set a new password:</p>
        <p>
            <a href="{{ reset_link }}" class="button">Reset Password</a>
        </p>
        <p>Or copy and paste this link in your browser:</p>
        <p><code>{{ reset_link }}</code></p>
        <p>This link expires in 1 hour.</p>
        <div class="footer">
            <p>If you didn't request a password reset, you can ignore this email. Your password will remain unchanged.</p>
        </div>
    </div>
</body>
</html>
"""


class EmailService:
    """Service for sending emails."""
    
    @staticmethod
    async def send_verification_email(email: str, verification_token: str) -> bool:
        """Send email verification link."""
        try:
            verification_link = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
            
            template = Template(VERIFICATION_EMAIL_TEMPLATE)
            html_content = template.render(
                app_name=settings.PROJECT_NAME,
                verification_link=verification_link
            )
            
            return await EmailService._send_email(
                to_email=email,
                subject=f"Verify your email - {settings.PROJECT_NAME}",
                html_content=html_content
            )
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            return False
    
    @staticmethod
    async def send_password_reset_email(email: str, reset_token: str) -> bool:
        """Send password reset link."""
        try:
            reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
            
            template = Template(PASSWORD_RESET_EMAIL_TEMPLATE)
            html_content = template.render(
                reset_link=reset_link
            )
            
            return await EmailService._send_email(
                to_email=email,
                subject=f"Password Reset - {settings.PROJECT_NAME}",
                html_content=html_content
            )
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False
    
    @staticmethod
    async def _send_email(to_email: str, subject: str, html_content: str) -> bool:
        """Internal method to send email via SMTP."""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            message["To"] = to_email
            
            # Attach HTML content
            part = MIMEText(html_content, "html")
            message.attach(part)
            
            # Send email
            async with aiosmtplib.SMTP(hostname=settings.SMTP_HOST, port=settings.SMTP_PORT) as smtp:
                await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                await smtp.sendmail(settings.SMTP_FROM_EMAIL, to_email, message.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
