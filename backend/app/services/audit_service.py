"""
Audit logging service
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from app.db.models.audit_log import AuditLog
from app.db.models.user import User
from app.core.config import settings


class AuditService:
    """Service for audit logging"""

    async def log_action(
        self,
        db: AsyncSession,
        action: str,
        user: Optional[User] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        changes: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """
        Log an action to the audit log

        Args:
            db: Database session
            action: Action type (CREATE, UPDATE, DELETE, LOGIN, etc.)
            user: User who performed the action
            entity_type: Type of entity affected
            entity_id: ID of affected entity
            changes: Dict of changes made
            request: FastAPI request object
        """
        if not settings.AUDIT_LOG_ENABLED:
            return

        # Get request details if provided
        ip_address = None
        user_agent = None
        correlation_id = None

        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            correlation_id = getattr(request.state, "correlation_id", None)

        # Create audit log entry
        audit_log = AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id
        )

        db.add(audit_log)
        await db.flush()


# Create singleton instance
audit_service = AuditService()
