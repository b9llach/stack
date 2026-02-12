"""
Session management service for tracking and revoking user sessions
"""
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import logging

from app.core.cache import cache_get, cache_set, cache_delete, get_redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class SessionInfo:
    """Session information container"""

    def __init__(
        self,
        session_id: str,
        user_id: int,
        created_at: str,
        last_used_at: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_type: Optional[str] = None,
        is_current: bool = False
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = created_at
        self.last_used_at = last_used_at
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.device_type = device_type
        self.is_current = is_current

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent[:100] if self.user_agent else None,
            "device_type": self.device_type,
            "is_current": self.is_current
        }


class SessionService:
    """
    Service for managing user sessions.

    Sessions are stored in Redis with the following structure:
    - session:{session_id} -> session data (JSON)
    - user_sessions:{user_id} -> set of session_ids
    """

    def __init__(self):
        self.session_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # Match refresh token expiry

    def _generate_session_id(self, token: str) -> str:
        """Generate a unique session ID from a token (hash for privacy)"""
        return hashlib.sha256(token.encode()).hexdigest()[:32]

    def _detect_device_type(self, user_agent: str) -> str:
        """Simple device type detection from user agent"""
        if not user_agent:
            return "unknown"

        user_agent_lower = user_agent.lower()

        if "mobile" in user_agent_lower or "android" in user_agent_lower:
            if "tablet" in user_agent_lower or "ipad" in user_agent_lower:
                return "tablet"
            return "mobile"
        elif "windows" in user_agent_lower or "macintosh" in user_agent_lower or "linux" in user_agent_lower:
            return "desktop"
        else:
            return "other"

    async def create_session(
        self,
        user_id: int,
        token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        Create a new session for a user.

        Args:
            user_id: User ID
            token: Access or refresh token
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Session ID
        """
        session_id = self._generate_session_id(token)
        now = datetime.now(timezone.utc).isoformat()

        session_data = {
            "user_id": user_id,
            "created_at": now,
            "last_used_at": now,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device_type": self._detect_device_type(user_agent or "")
        }

        # Store session data
        await cache_set(
            f"session:{session_id}",
            json.dumps(session_data),
            ttl=self.session_ttl
        )

        # Add session to user's session set
        redis = await get_redis()
        await redis.sadd(f"user_sessions:{user_id}", session_id)
        await redis.expire(f"user_sessions:{user_id}", self.session_ttl)

        logger.info(
            f"Session created for user {user_id}",
            extra={"session_id": session_id[:8], "user_id": user_id}
        )

        return session_id

    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get session information.

        Args:
            session_id: Session ID

        Returns:
            SessionInfo or None if not found
        """
        data = await cache_get(f"session:{session_id}")
        if not data:
            return None

        if isinstance(data, str):
            data = json.loads(data)

        return SessionInfo(
            session_id=session_id,
            user_id=data["user_id"],
            created_at=data["created_at"],
            last_used_at=data["last_used_at"],
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            device_type=data.get("device_type")
        )

    async def update_session_activity(self, token: str) -> None:
        """
        Update the last_used_at timestamp for a session.

        Args:
            token: The token used in the request
        """
        session_id = self._generate_session_id(token)
        data = await cache_get(f"session:{session_id}")

        if data:
            if isinstance(data, str):
                data = json.loads(data)

            data["last_used_at"] = datetime.now(timezone.utc).isoformat()

            await cache_set(
                f"session:{session_id}",
                json.dumps(data),
                ttl=self.session_ttl
            )

    async def get_user_sessions(
        self,
        user_id: int,
        current_token: Optional[str] = None
    ) -> List[SessionInfo]:
        """
        Get all active sessions for a user.

        Args:
            user_id: User ID
            current_token: Current token to mark as "current session"

        Returns:
            List of SessionInfo objects
        """
        redis = await get_redis()
        session_ids = await redis.smembers(f"user_sessions:{user_id}")

        if not session_ids:
            return []

        current_session_id = None
        if current_token:
            current_session_id = self._generate_session_id(current_token)

        sessions = []
        expired_sessions = []

        for session_id in session_ids:
            session = await self.get_session(session_id)
            if session:
                session.is_current = (session_id == current_session_id)
                sessions.append(session)
            else:
                # Session expired, mark for cleanup
                expired_sessions.append(session_id)

        # Clean up expired sessions
        if expired_sessions:
            await redis.srem(f"user_sessions:{user_id}", *expired_sessions)

        # Sort by last_used_at descending
        sessions.sort(key=lambda s: s.last_used_at, reverse=True)

        return sessions

    async def revoke_session(self, user_id: int, session_id: str) -> bool:
        """
        Revoke a specific session.

        Args:
            user_id: User ID (for verification)
            session_id: Session ID to revoke

        Returns:
            True if session was revoked
        """
        # Verify session belongs to user
        session = await self.get_session(session_id)
        if not session or session.user_id != user_id:
            return False

        # Delete session data
        await cache_delete(f"session:{session_id}")

        # Remove from user's session set
        redis = await get_redis()
        await redis.srem(f"user_sessions:{user_id}", session_id)

        logger.info(
            f"Session revoked for user {user_id}",
            extra={"session_id": session_id[:8], "user_id": user_id}
        )

        return True

    async def revoke_all_sessions(self, user_id: int, except_current: Optional[str] = None) -> int:
        """
        Revoke all sessions for a user.

        Args:
            user_id: User ID
            except_current: Token to keep (current session)

        Returns:
            Number of sessions revoked
        """
        current_session_id = None
        if except_current:
            current_session_id = self._generate_session_id(except_current)

        redis = await get_redis()
        session_ids = await redis.smembers(f"user_sessions:{user_id}")

        revoked_count = 0
        for session_id in session_ids:
            if session_id != current_session_id:
                await cache_delete(f"session:{session_id}")
                await redis.srem(f"user_sessions:{user_id}", session_id)
                revoked_count += 1

        logger.info(
            f"Revoked {revoked_count} sessions for user {user_id}",
            extra={"user_id": user_id, "revoked_count": revoked_count}
        )

        return revoked_count


# Singleton instance
session_service = SessionService()
