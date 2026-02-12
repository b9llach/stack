"""
Email service for sending emails via SMTP
"""
from typing import List, Optional
import logging
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib

from app.core.config import settings
from app.core.cache import cache_set, cache_get, cache_delete

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending emails via SMTP
    """

    def __init__(self):
        """
        Initialize email service with SMTP configuration
        """
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_tls = settings.SMTP_TLS
        self.from_email = settings.EMAILS_FROM_EMAIL or settings.SMTP_USER
        self.from_name = settings.EMAILS_FROM_NAME

    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        html: Optional[str] = None
    ) -> bool:
        """
        Send an email via SMTP

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Plain text email body
            html: Optional HTML email body

        Returns:
            True if email sent successfully
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = ", ".join(to)

            # Add plain text version
            text_part = MIMEText(body, "plain")
            message.attach(text_part)

            # Add HTML version if provided
            if html:
                html_part = MIMEText(html, "html")
                message.attach(html_part)

            # Send email
            if self.smtp_tls:
                await aiosmtplib.send(
                    message,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.smtp_user,
                    password=self.smtp_password,
                    start_tls=True
                )
            else:
                await aiosmtplib.send(
                    message,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.smtp_user,
                    password=self.smtp_password
                )

            logger.info(f"Email sent successfully to {to} with subject: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False

    async def send_welcome_email(
        self,
        to: str,
        username: str
    ) -> bool:
        """
        Send welcome email to new user

        Args:
            to: Recipient email address
            username: Username

        Returns:
            True if email sent successfully
        """
        subject = f"Welcome to {settings.PROJECT_NAME}"

        body = f"""
Hello {username},

Welcome to {settings.PROJECT_NAME}!

Your account has been successfully created. You can now log in and start using our services.

If you didn't create this account, please contact our support team immediately.

Best regards,
The {settings.PROJECT_NAME} Team
"""

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to {settings.PROJECT_NAME}</h1>
        </div>
        <div class="content">
            <h2>Hello {username},</h2>
            <p>Your account has been successfully created. You can now log in and start using our services.</p>
            <p>If you didn't create this account, please contact our support team immediately.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>The {settings.PROJECT_NAME} Team</p>
        </div>
    </div>
</body>
</html>
"""

        return await self.send_email([to], subject, body, html)

    async def send_password_reset_email(
        self,
        to: str,
        reset_token: str
    ) -> bool:
        """
        Send password reset email

        Args:
            to: Recipient email address
            reset_token: Password reset token

        Returns:
            True if email sent successfully
        """
        subject = "Password Reset Request"

        body = f"""
Hello,

You have requested to reset your password for {settings.PROJECT_NAME}.

Your password reset token is: {reset_token}

This token will expire in 1 hour.

If you didn't request this password reset, please ignore this email.

Best regards,
The {settings.PROJECT_NAME} Team
"""

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #FF5722; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .token {{ background-color: #fff; padding: 15px; border: 2px solid #FF5722;
                  font-size: 20px; font-weight: bold; text-align: center; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Request</h1>
        </div>
        <div class="content">
            <p>You have requested to reset your password for {settings.PROJECT_NAME}.</p>
            <p>Your password reset token is:</p>
            <div class="token">{reset_token}</div>
            <p>This token will expire in 1 hour.</p>
            <p>If you didn't request this password reset, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>The {settings.PROJECT_NAME} Team</p>
        </div>
    </div>
</body>
</html>
"""

        return await self.send_email([to], subject, body, html)

    async def generate_2fa_code(self, user_id: int) -> str:
        """
        Generate a 6-digit 2FA code and store it in cache

        Args:
            user_id: User ID

        Returns:
            6-digit code
        """
        # Generate random 6-digit code
        code = ''.join(random.choices(string.digits, k=6))

        # Store in cache with expiration
        cache_key = f"2fa:{user_id}"
        await cache_set(
            cache_key,
            code,
            ttl=settings.TWO_FA_CODE_EXPIRE_MINUTES * 60
        )

        logger.info(f"2FA code generated for user {user_id}")
        return code

    async def verify_2fa_code(self, user_id: int, code: str) -> tuple[bool, str]:
        """
        Verify 2FA code with brute-force protection

        Args:
            user_id: User ID
            code: Code to verify

        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if code is valid
            - (False, error_message) if invalid or locked out
        """
        max_attempts = settings.TWO_FA_MAX_ATTEMPTS
        lockout_minutes = settings.TWO_FA_LOCKOUT_MINUTES

        attempts_key = f"2fa_attempts:{user_id}"
        cache_key = f"2fa:{user_id}"

        # Check if user is locked out
        attempts = await cache_get(attempts_key)
        if attempts and int(attempts) >= max_attempts:
            logger.warning(f"2FA locked out for user {user_id}")
            return False, f"Too many failed attempts. Try again in {lockout_minutes} minutes."

        stored_code = await cache_get(cache_key)

        if stored_code and stored_code == code:
            # Delete the code and reset attempts after successful verification
            await cache_delete(cache_key)
            await cache_delete(attempts_key)
            logger.info(f"2FA code verified for user {user_id}")
            return True, ""

        # Increment failed attempts
        current_attempts = int(attempts) if attempts else 0
        new_attempts = current_attempts + 1
        await cache_set(attempts_key, str(new_attempts), ttl=lockout_minutes * 60)

        remaining = max_attempts - new_attempts
        logger.warning(f"Invalid 2FA code attempt for user {user_id}. {remaining} attempts remaining.")

        if remaining <= 0:
            return False, f"Too many failed attempts. Try again in {lockout_minutes} minutes."

        return False, f"Invalid code. {remaining} attempts remaining."

    async def send_2fa_email(
        self,
        to: str,
        username: str,
        code: str
    ) -> bool:
        """
        Send 2FA code email

        Args:
            to: Recipient email address
            username: Username
            code: 2FA code

        Returns:
            True if email sent successfully
        """
        subject = "Your Two-Factor Authentication Code"

        body = f"""
Hello {username},

Your two-factor authentication code is: {code}

This code will expire in {settings.TWO_FA_CODE_EXPIRE_MINUTES} minutes.

If you didn't request this code, please secure your account immediately.

Best regards,
The {settings.PROJECT_NAME} Team
"""

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .code {{ background-color: #fff; padding: 20px; border: 3px solid #2196F3;
                 font-size: 32px; font-weight: bold; text-align: center;
                 letter-spacing: 5px; margin: 20px 0; font-family: monospace; }}
        .warning {{ background-color: #FFF3E0; padding: 15px; border-left: 4px solid #FF9800; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Two-Factor Authentication</h1>
        </div>
        <div class="content">
            <h2>Hello {username},</h2>
            <p>Your two-factor authentication code is:</p>
            <div class="code">{code}</div>
            <p>This code will expire in {settings.TWO_FA_CODE_EXPIRE_MINUTES} minutes.</p>
            <div class="warning">
                <strong>Security Notice:</strong> If you didn't request this code,
                please secure your account immediately.
            </div>
        </div>
        <div class="footer">
            <p>Best regards,<br>The {settings.PROJECT_NAME} Team</p>
        </div>
    </div>
</body>
</html>
"""

        return await self.send_email([to], subject, body, html)

    async def send_verification_email(
        self,
        to: str,
        username: str,
        verification_token: str
    ) -> bool:
        """
        Send email verification link

        Args:
            to: Recipient email address
            username: Username
            verification_token: Email verification token

        Returns:
            True if email sent successfully
        """
        # In production, you would have a proper frontend URL
        verification_link = f"http://localhost:8000/api/v1/auth/verify-email?token={verification_token}"

        subject = "Verify Your Email Address"

        body = f"""
Hello {username},

Thank you for registering with {settings.PROJECT_NAME}!

Please verify your email address by clicking the link below:
{verification_link}

Or use this verification token: {verification_token}

This link will expire in 24 hours.

If you didn't create this account, please ignore this email.

Best regards,
The {settings.PROJECT_NAME} Team
"""

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .button {{ display: inline-block; padding: 15px 30px; background-color: #4CAF50;
                   color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .token {{ background-color: #fff; padding: 10px; border: 1px solid #ddd;
                  font-family: monospace; word-break: break-all; }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Verify Your Email</h1>
        </div>
        <div class="content">
            <h2>Hello {username},</h2>
            <p>Thank you for registering with {settings.PROJECT_NAME}!</p>
            <p>Please verify your email address by clicking the button below:</p>
            <div style="text-align: center;">
                <a href="{verification_link}" class="button">Verify Email Address</a>
            </div>
            <p>Or use this verification token:</p>
            <div class="token">{verification_token}</div>
            <p><small>This link will expire in 24 hours.</small></p>
            <p>If you didn't create this account, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>The {settings.PROJECT_NAME} Team</p>
        </div>
    </div>
</body>
</html>
"""

        return await self.send_email([to], subject, body, html)


# Create singleton instance
email_service = EmailService()
