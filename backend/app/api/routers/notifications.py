"""
Notification endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List

from app.core.async_database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.db.models.user import User
from app.db.models.notification import Notification, DeviceToken
from app.services.notification_service import notification_service
from app.tasks.notification_tasks import send_push_notification


router = APIRouter()


class DeviceTokenCreate(BaseModel):
    token: str
    device_type: str  # ios, android, web


class SendNotificationRequest(BaseModel):
    title: str
    body: str
    data: Optional[dict] = None


@router.post("/device-tokens")
async def register_device_token(
    request: DeviceTokenCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Register device token for push notifications"""
    # Check if token already exists
    result = await db.execute(
        select(DeviceToken).where(DeviceToken.token == request.token)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing token
        existing.user_id = current_user.id
        existing.device_type = request.device_type
        existing.is_active = True
        db.add(existing)
    else:
        # Create new token
        device_token = DeviceToken(
            user_id=current_user.id,
            token=request.token,
            device_type=request.device_type
        )
        db.add(device_token)

    await db.commit()
    return {"message": "Device token registered successfully"}


@router.get("/")
async def get_notifications(
    skip: int = 0,
    limit: int = 20,
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's notifications"""
    query = select(Notification).where(Notification.user_id == current_user.id)

    if unread_only:
        query = query.where(Notification.is_read == False)

    query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()

    return {
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "body": n.body,
                "data": n.data,
                "is_read": n.is_read,
                "created_at": n.created_at
            }
            for n in notifications
        ]
    }


@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark notification as read"""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    from datetime import datetime, timezone
    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)
    db.add(notification)
    await db.commit()

    return {"message": "Notification marked as read"}


@router.post("/send-test")
async def send_test_notification(
    request: SendNotificationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send test push notification to current user"""
    # Create in-app notification
    notification = await notification_service.create_in_app_notification(
        db=db,
        user_id=current_user.id,
        title=request.title,
        body=request.body,
        data=request.data
    )
    await db.commit()

    # Queue push notification
    send_push_notification.delay(
        user_id=current_user.id,
        title=request.title,
        body=request.body,
        data=request.data
    )

    return {"message": "Test notification sent", "notification_id": notification.id}
