"""
Security utilities for authentication and authorization
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.core.config import settings


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    # Convert password to bytes and hash it
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string for database storage
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches
    """
    # Convert to bytes
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    # Verify password
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token

    Args:
        data: Data to encode in token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token

    Args:
        data: Data to encode in token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str, expected_type: Optional[str] = "access") -> Dict[str, Any]:
    """
    Decode and verify a JWT token

    Args:
        token: JWT token to decode
        expected_type: Expected token type ("access" or "refresh"). Set to None to skip validation.

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid, expired, or wrong type
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Validate token type if specified
        if expected_type is not None:
            token_type = payload.get("type")
            if token_type != expected_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {expected_type} token.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_api_key(api_key: str) -> bool:
    """
    Verify an API key

    Args:
        api_key: API key to verify

    Returns:
        True if valid

    Note:
        Configure API_KEYS in settings or implement database lookup.
        For production, store hashed API keys and use constant-time comparison.
    """
    import hmac

    # Get valid API keys from settings (should be configured in .env)
    valid_keys = getattr(settings, 'API_KEYS', [])

    if not valid_keys:
        # No API keys configured - reject all requests
        return False

    # Use constant-time comparison to prevent timing attacks
    for valid_key in valid_keys:
        if hmac.compare_digest(api_key, valid_key):
            return True

    return False


async def blacklist_token(token: str) -> bool:
    """
    Add a token to the blacklist (for logout)

    Args:
        token: JWT token to blacklist

    Returns:
        True if successful
    """
    from app.core.cache import cache_set

    try:
        # Decode token to get expiration time
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        exp = payload.get("exp")

        if exp:
            # Calculate TTL until token expires
            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
            ttl = int((exp_datetime - datetime.now(timezone.utc)).total_seconds())

            if ttl > 0:
                # Store in blacklist with TTL matching token expiration
                await cache_set(f"blacklist:{token}", "1", ttl=ttl)
                return True

        return False
    except JWTError:
        return False


async def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token is blacklisted

    Args:
        token: JWT token to check

    Returns:
        True if token is blacklisted
    """
    from app.core.cache import cache_get

    result = await cache_get(f"blacklist:{token}")
    return result is not None


def create_password_reset_token(user_id: int) -> str:
    """
    Create a password reset token

    Args:
        user_id: User ID

    Returns:
        Password reset token (valid for 1 hour)
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode = {
        "sub": str(user_id),
        "type": "password_reset",
        "exp": expire
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_password_reset_token(token: str) -> int:
    """
    Decode and validate a password reset token

    Args:
        token: Password reset token

    Returns:
        User ID from token

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid password reset token"
            )

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid password reset token"
            )

        return int(user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token"
        )


def create_email_verification_token(user_id: int) -> str:
    """
    Create an email verification token

    Args:
        user_id: User ID

    Returns:
        Email verification token (valid for 24 hours)
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode = {
        "sub": str(user_id),
        "type": "email_verification",
        "exp": expire
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_email_verification_token(token: str) -> int:
    """
    Decode and validate an email verification token

    Args:
        token: Email verification token

    Returns:
        User ID from token

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        if payload.get("type") != "email_verification":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email verification token"
            )

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email verification token"
            )

        return int(user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired email verification token"
        )
