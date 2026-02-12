"""
Firebase Cloud Messaging notification service
"""
import firebase_admin
from firebase_admin import credentials, messaging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.models.notification import Notification, DeviceToken


class NotificationService:
    """Service for handling push notifications via Firebase"""

    def __init__(self):
        self.initialized = False
        if settings.FIREBASE_ENABLED and settings.FIREBASE_CREDENTIALS_PATH:
            try:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
                self.initialized = True
            except Exception as e:
                print(f"Failed to initialize Firebase: {e}")

    async def send_to_user(
        self,
        user_id: int,
        title: str,
        body: str,
        data: dict = None
    ) -> bool:
        """
        Send push notification to a specific user

        Args:
            user_id: User ID to send to
            title: Notification title
            body: Notification body
            data: Additional data payload

        Returns:
            True if sent successfully
        """
        if not self.initialized:
            return False

        # This would need database session to get user tokens
        # For now, returning False
        # In production, pass db session and query user's device tokens
        return False

    async def send_to_token(
        self,
        token: str,
        title: str,
        body: str,
        data: dict = None
    ) -> bool:
        """
        Send push notification to a specific device token

        Args:
            token: FCM device token
            title: Notification title
            body: Notification body
            data: Additional data payload

        Returns:
            True if sent successfully
        """
        if not self.initialized:
            return False

        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                token=token
            )

            response = messaging.send(message)
            return True
        except Exception as e:
            print(f"Error sending notification: {e}")
            return False

    async def send_to_multiple_users(
        self,
        user_ids: List[int],
        title: str,
        body: str,
        data: dict = None
    ) -> int:
        """
        Send push notification to multiple users

        Args:
            user_ids: List of user IDs
            title: Notification title
            body: Notification body
            data: Additional data payload

        Returns:
            Number of successfully sent notifications
        """
        if not self.initialized:
            return 0

        # This would need database session
        # For now, returning 0
        return 0

    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: dict = None
    ) -> bool:
        """
        Send push notification to a topic

        Args:
            topic: Topic name
            title: Notification title
            body: Notification body
            data: Additional data payload

        Returns:
            True if sent successfully
        """
        if not self.initialized:
            return False

        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                topic=topic
            )

            response = messaging.send(message)
            return True
        except Exception as e:
            print(f"Error sending notification to topic: {e}")
            return False

    async def create_in_app_notification(
        self,
        db: AsyncSession,
        user_id: int,
        title: str,
        body: str,
        data: dict = None
    ) -> Notification:
        """
        Create in-app notification

        Args:
            db: Database session
            user_id: User ID
            title: Notification title
            body: Notification body
            data: Additional data

        Returns:
            Created notification
        """
        notification = Notification(
            user_id=user_id,
            title=title,
            body=body,
            data=data
        )
        db.add(notification)
        await db.flush()
        await db.refresh(notification)
        return notification


# Create singleton instance
notification_service = NotificationService()
