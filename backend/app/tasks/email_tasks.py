"""
Email background tasks
"""
from app.core.celery_app import celery_app
from app.services.email_service import email_service


@celery_app.task(name="send_welcome_email")
def send_welcome_email(email: str, username: str):
    """
    Send welcome email to new user

    Args:
        email: User email address
        username: Username
    """
    import asyncio

    async def _send():
        await email_service.send_email(
            to=[email],
            subject="Welcome to FastAPI Template",
            body=f"Welcome {username}! Thank you for registering.",
            html=f"<h1>Welcome {username}!</h1><p>Thank you for registering.</p>"
        )

    asyncio.run(_send())


@celery_app.task(name="send_bulk_email")
def send_bulk_email(recipients: list[str], subject: str, body: str, html: str = None):
    """
    Send email to multiple recipients

    Args:
        recipients: List of email addresses
        subject: Email subject
        body: Plain text body
        html: HTML body (optional)
    """
    import asyncio

    async def _send():
        await email_service.send_email(
            to=recipients,
            subject=subject,
            body=body,
            html=html
        )

    asyncio.run(_send())


@celery_app.task(name="send_password_reset_email")
def send_password_reset_email(email: str, reset_token: str):
    """
    Send password reset email

    Args:
        email: User email address
        reset_token: Password reset token
    """
    import asyncio
    from app.core.config import settings

    reset_url = f"{settings.HOST}:{settings.PORT}/reset-password?token={reset_token}"

    async def _send():
        await email_service.send_email(
            to=[email],
            subject="Password Reset Request",
            body=f"Click this link to reset your password: {reset_url}",
            html=f"<p>Click <a href='{reset_url}'>here</a> to reset your password.</p>"
        )

    asyncio.run(_send())
