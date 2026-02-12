"""
Authentication dependencies
"""
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import time
import logging

from app.core.async_database import get_db
from app.core.security import decode_token, verify_api_key, is_token_blacklisted
from app.db.models.user import User
from app.db.models.enums import UserRole
from app.db.utils.user_crud import user_crud
from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()


def rate_limit_endpoint(max_requests: int = 5, window_seconds: int = 60):
    """
    Dependency factory for per-endpoint rate limiting.

    Use this on sensitive endpoints like login, registration, password reset.

    Args:
        max_requests: Maximum requests allowed in the window
        window_seconds: Time window in seconds

    Example:
        @router.post("/login")
        async def login(
            _: None = Depends(rate_limit_endpoint(max_requests=5, window_seconds=60))
        ):
            ...
    """
    async def rate_limiter(request: Request):
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.headers.get("X-Real-IP", "")
        if not client_ip and request.client:
            client_ip = request.client.host

        endpoint = request.url.path
        current_time = int(time.time())
        window_key = current_time // window_seconds
        redis_key = f"endpoint_ratelimit:{endpoint}:{client_ip}:{window_key}"

        try:
            from app.core.cache import get_redis

            redis = await get_redis()

            pipe = redis.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, window_seconds + 1)
            results = await pipe.execute()

            request_count = results[0]

            if request_count > max_requests:
                retry_after = window_seconds - (current_time % window_seconds)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )

        except HTTPException:
            raise
        except Exception as e:
            # Fail open if Redis is unavailable
            logger.warning(f"Endpoint rate limiting failed (allowing request): {e}")

    return rate_limiter


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: Bearer token credentials
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid, blacklisted, or user not found
    """
    token = credentials.credentials

    # Check if token is blacklisted (logged out)
    if await is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )

    payload = decode_token(token)

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    # Fetch user from database
    user = await user_crud.get(db, int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user

    Args:
        current_user: Current user from get_current_user

    Returns:
        Active user object

    Raises:
        HTTPException: If user is inactive
    """
    if not await user_crud.is_active(current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current admin or superadmin user

    Args:
        current_user: Current active user

    Returns:
        Admin user object

    Raises:
        HTTPException: If user is not admin or superadmin
    """
    if not await user_crud.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin role required."
        )
    return current_user


async def get_current_superadmin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current superadmin user

    Args:
        current_user: Current active user

    Returns:
        Superadmin user object

    Raises:
        HTTPException: If user is not superadmin
    """
    if not await user_crud.is_superadmin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Superadmin role required."
        )
    return current_user


def require_role(required_role: UserRole):
    """
    Dependency factory to require specific role

    Args:
        required_role: Required user role

    Returns:
        Dependency function

    Example:
        @app.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role(UserRole.ADMIN))):
            ...
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not await user_crud.has_role(current_user, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. {required_role.value} role required."
            )
        return current_user
    return role_checker


def require_any_role(*roles: UserRole):
    """
    Dependency factory to require any of specified roles

    Args:
        *roles: Required user roles (any of them)

    Returns:
        Dependency function

    Example:
        @app.get("/staff-only")
        async def staff_endpoint(
            user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPERADMIN))
        ):
            ...
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        # Check if user has any of the required roles
        for role in roles:
            if await user_crud.has_role(current_user, role):
                return current_user

        role_names = ", ".join([role.value for role in roles])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. One of these roles required: {role_names}"
        )
    return role_checker


async def verify_api_key_dependency(
    x_api_key: Optional[str] = Header(None)
):
    """
    Verify API key from header

    Args:
        x_api_key: API key from header

    Returns:
        True if valid

    Raises:
        HTTPException: If API key is invalid
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    if not verify_api_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return True
