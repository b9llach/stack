"""
Notification background tasks
"""
from app.core.celery_app import celery_app


@celery_app.task(name="send_push_notification")
def send_push_notification(user_id: int, title: str, body: str, data: dict = None):
    """
    Send push notification to user via Firebase

    Args:
        user_id: User ID
        title: Notification title
        body: Notification body
        data: Additional data payload
    """
    import asyncio
    from app.services.notification_service import notification_service

    async def _send():
        await notification_service.send_to_user(
            user_id=user_id,
            title=title,
            body=body,
            data=data or {}
        )

    asyncio.run(_send())


@celery_app.task(name="send_bulk_notification")
def send_bulk_notification(user_ids: list[int], title: str, body: str, data: dict = None):
    """
    Send push notification to multiple users

    Args:
        user_ids: List of user IDs
        title: Notification title
        body: Notification body
        data: Additional data payload
    """
    import asyncio
    from app.services.notification_service import notification_service

    async def _send():
        await notification_service.send_to_multiple_users(
            user_ids=user_ids,
            title=title,
            body=body,
            data=data or {}
        )

    asyncio.run(_send())


@celery_app.task(name="send_topic_notification")
def send_topic_notification(topic: str, title: str, body: str, data: dict = None):
    """
    Send push notification to a topic

    Args:
        topic: Topic name
        title: Notification title
        body: Notification body
        data: Additional data payload
    """
    import asyncio
    from app.services.notification_service import notification_service

    async def _send():
        await notification_service.send_to_topic(
            topic=topic,
            title=title,
            body=body,
            data=data or {}
        )

    asyncio.run(_send())
