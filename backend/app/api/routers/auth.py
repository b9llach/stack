"""
Authentication endpoints including 2FA
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import secrets

from app.core.async_database import get_db
from app.api.dependencies.auth import get_current_active_user, rate_limit_endpoint
from app.db.models.user import User
from app.db.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    UserSettings,
    TwoFactorRequest,
    RefreshTokenRequest,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TOTPDisableRequest
)
from app.services.user_service import user_service
from app.services.email_service import email_service
from app.db.utils.user_crud import user_crud
from app.core.config import settings
from app.core.cache import cache_set, cache_get, cache_delete

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_endpoint(max_requests=5, window_seconds=60))
):
    """
    Register a new user (public endpoint)
    Rate limited: 5 requests per minute per IP
    Sends verification email automatically.
    """
    from app.core.security import create_email_verification_token

    user = await user_service.create_user(db, user_in)

    # Send verification email
    verification_token = create_email_verification_token(user.id)
    await email_service.send_verification_email(
        to=user.email,
        username=user.username,
        verification_token=verification_token
    )

    return user


@router.post("/login")
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_endpoint(max_requests=10, window_seconds=60))
):
    """
    Login endpoint - initiates 2FA if enabled for user
    Supports login with username or email
    Rate limited: 10 requests per minute per IP
    """
    # Authenticate user credentials (supports username or email)
    # Returns (user, error_message) tuple with brute-force protection
    user, error_message = await user_crud.authenticate(
        db,
        credentials.username_or_email,
        credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_message or "Incorrect username/email or password"
        )

    if not await user_crud.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Check if user has TOTP enabled (authenticator app - takes priority)
    if user.totp_enabled:
        # Generate a temporary session token for TOTP verification
        session_token = secrets.token_urlsafe(32)
        await cache_set(
            f"totp_login:{session_token}",
            str(user.id),
            ttl=300  # 5 minutes to enter TOTP code
        )

        return {
            "message": "Please enter the code from your authenticator app",
            "requires_2fa": True,
            "two_fa_type": "totp",
            "session_token": session_token
        }
    # Check if user has email 2FA enabled
    elif user.two_fa_enabled:
        # Generate and send 2FA code
        code = await email_service.generate_2fa_code(user.id)
        await email_service.send_2fa_email(
            to=user.email,
            username=user.username,
            code=code
        )

        # Generate a temporary session token instead of exposing user_id
        session_token = secrets.token_urlsafe(32)
        await cache_set(
            f"2fa_session:{session_token}",
            str(user.id),
            ttl=settings.TWO_FA_CODE_EXPIRE_MINUTES * 60
        )

        return {
            "message": "2FA code sent to your email",
            "requires_2fa": True,
            "two_fa_type": "email",
            "session_token": session_token  # Use opaque token instead of user_id
        }
    else:
        # No 2FA, return tokens directly and update last_login_at
        from datetime import datetime, timezone
        from app.services.session_service import session_service

        user.last_login_at = datetime.now(timezone.utc)
        db.add(user)
        await db.commit()

        tokens = await user_service.authenticate_user(
            db,
            credentials.username_or_email,
            credentials.password
        )

        # Create session for tracking (non-blocking, don't fail if Redis is down)
        try:
            await session_service.create_session(
                user_id=user.id,
                token=tokens["access_token"],
                ip_address=None,  # Will be set from request in middleware
                user_agent=None
            )
        except Exception:
            pass  # Session tracking is optional

        return tokens


@router.post("/verify-2fa", response_model=Token)
async def verify_2fa(
    request: TwoFactorRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_endpoint(max_requests=10, window_seconds=60))
):
    """
    Verify 2FA code and complete login
    Rate limited: 10 requests per minute per IP
    """
    # Get user_id from session token
    user_id_str = await cache_get(f"2fa_session:{request.session_token}")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please login again."
        )

    user_id = int(user_id_str)

    # Verify the 2FA code (with brute-force protection)
    is_valid, error_message = await email_service.verify_2fa_code(user_id, request.code)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_message or "Invalid or expired 2FA code"
        )

    # Delete the session token after successful verification
    await cache_delete(f"2fa_session:{request.session_token}")

    # Get user and generate tokens
    user = await user_service.get_user_by_id(db, user_id)

    # Update last login timestamp
    from datetime import datetime, timezone
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()

    from app.core.security import create_access_token, create_refresh_token

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        }
    )
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        }
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/enable-2fa")
async def enable_2fa(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Enable 2FA for current user
    """
    if current_user.two_fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled"
        )

    # Check if email is verified
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please verify your email before enabling 2FA"
        )

    # Enable 2FA
    current_user.two_fa_enabled = True
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    # Send confirmation email
    await email_service.send_email(
        to=[current_user.email],
        subject="2FA Enabled",
        body=f"Two-factor authentication has been enabled for your account.",
        html=f"<p>Two-factor authentication has been successfully enabled for your account.</p>"
    )

    return {
        "message": "2FA has been enabled successfully",
        "two_fa_enabled": True
    }


@router.post("/disable-2fa")
async def disable_2fa(
    password: str = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disable 2FA for current user (requires password confirmation)
    OAuth users must verify via email code instead.
    """
    if not current_user.two_fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled"
        )

    # OAuth-only users cannot disable 2FA with password
    if current_user.hashed_password is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth users cannot disable 2FA with password. Contact support."
        )

    # Verify password for security
    from app.core.security import verify_password
    if not verify_password(password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )

    # Disable 2FA
    current_user.two_fa_enabled = False
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    # Send notification email
    await email_service.send_email(
        to=[current_user.email],
        subject="2FA Disabled",
        body=f"Two-factor authentication has been disabled for your account. If this wasn't you, please secure your account immediately.",
        html=f"<p>Two-factor authentication has been disabled for your account.</p><p>If this wasn't you, please secure your account immediately.</p>"
    )

    return {
        "message": "2FA has been disabled successfully",
        "two_fa_enabled": False
    }


@router.post("/test-2fa")
async def test_2fa(
    current_user: User = Depends(get_current_active_user)
):
    """
    Send a test 2FA code to verify email configuration
    """
    # Generate test code
    code = await email_service.generate_2fa_code(current_user.id)

    # Send test email
    success = await email_service.send_2fa_email(
        to=current_user.email,
        username=current_user.username,
        code=code
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test email. Check SMTP configuration."
        )

    return {
        "message": "Test 2FA code sent to your email",
        "email": current_user.email
    }


# Google OAuth endpoints
@router.get("/google/login")
async def google_login(request: Request):
    """
    Initiate Google OAuth login flow

    Redirects user to Google's OAuth consent screen
    """
    if not settings.GOOGLE_OAUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not enabled. Set GOOGLE_OAUTH_ENABLED=True in environment."
        )

    from app.core.oauth import oauth

    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", response_model=Token)
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Google OAuth callback

    After user authorizes, Google redirects here with auth code.
    This endpoint exchanges the code for user info and creates/logs in the user.
    """
    if not settings.GOOGLE_OAUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not enabled"
        )

    from app.core.oauth import oauth, validate_google_user_info
    from app.core.security import create_access_token, create_refresh_token
    from datetime import datetime, timezone

    try:
        # Exchange authorization code for access token
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to authorize with Google: {str(e)}"
        )

    # Get user info from Google
    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info from Google"
        )

    # Validate and extract user data
    validated_data = validate_google_user_info(user_info)

    # Get or create user
    user, created = await user_crud.get_or_create_oauth_user(
        db=db,
        email=validated_data['email'],
        username=validated_data['username'],
        oauth_provider=validated_data['oauth_provider'],
        oauth_id=validated_data['oauth_id'],
        first_name=validated_data.get('first_name'),
        last_name=validated_data.get('last_name'),
        avatar_url=validated_data.get('avatar_url'),
        email_verified=validated_data.get('email_verified', False)
    )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()

    # Generate JWT tokens
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        }
    )
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        }
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using a valid refresh token
    """
    from app.core.security import decode_token, create_access_token, create_refresh_token

    # Decode and validate refresh token (explicitly check for refresh type)
    payload = decode_token(request.refresh_token, expected_type="refresh")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Verify user still exists and is active
    user = await user_crud.get(db, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )

    # Generate new tokens
    new_access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        }
    )
    new_refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        }
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """
    Logout user by blacklisting their current token

    The token will be invalidated and cannot be used again.
    """
    from app.core.security import blacklist_token
    from fastapi.security import HTTPAuthorizationCredentials

    # Get the token from the Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        await blacklist_token(token)

    return {"message": "Successfully logged out"}


@router.post("/request-password-reset")
async def request_password_reset(
    email: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_endpoint(max_requests=3, window_seconds=60))
):
    """
    Request a password reset email

    Always returns success to prevent email enumeration.
    Rate limited: 3 requests per minute per IP
    """
    from app.core.security import create_password_reset_token

    user = await user_crud.get_by_email(db, email)

    if user and user.hashed_password is not None:
        # Only send reset email if user exists and has a password
        # (OAuth-only users can't reset password)
        reset_token = create_password_reset_token(user.id)
        await email_service.send_password_reset_email(user.email, reset_token)

    # Always return success to prevent email enumeration
    return {
        "message": "If an account exists with that email, a password reset link has been sent."
    }


@router.post("/reset-password")
async def reset_password(
    token: str = Body(...),
    new_password: str = Body(...),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_endpoint(max_requests=5, window_seconds=60))
):
    """
    Reset password using a valid reset token
    Rate limited: 5 requests per minute per IP
    """
    from app.core.security import decode_password_reset_token, hash_password
    from app.utils.validators import validate_password_strength

    # Validate password strength
    is_valid, error_message = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Decode and validate token
    user_id = decode_password_reset_token(token)

    # Get user
    user = await user_crud.get(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )

    # OAuth-only users cannot set password this way
    if user.oauth_provider and user.hashed_password is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth users cannot reset password. Please login with your OAuth provider."
        )

    # Update password
    user.hashed_password = hash_password(new_password)
    db.add(user)
    await db.commit()

    # Send confirmation email
    await email_service.send_email(
        to=[user.email],
        subject="Password Changed",
        body="Your password has been successfully changed. If you didn't do this, contact support immediately.",
        html="<p>Your password has been successfully changed.</p><p>If you didn't do this, contact support immediately.</p>"
    )

    return {"message": "Password has been reset successfully"}


@router.get("/verify-email")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify email address using the token sent to user's email
    """
    from app.core.security import decode_email_verification_token

    user_id = decode_email_verification_token(token)

    user = await user_crud.get(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )

    if user.email_verified:
        return {"message": "Email already verified"}

    user.email_verified = True
    db.add(user)
    await db.commit()

    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification_email(
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(rate_limit_endpoint(max_requests=3, window_seconds=60))
):
    """
    Resend email verification link
    Rate limited: 3 requests per minute
    """
    from app.core.security import create_email_verification_token

    if current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )

    verification_token = create_email_verification_token(current_user.id)
    await email_service.send_verification_email(
        to=current_user.email,
        username=current_user.username,
        verification_token=verification_token
    )

    return {"message": "Verification email sent"}


@router.post("/change-password")
async def change_password(
    current_password: str = Body(...),
    new_password: str = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change password for authenticated user
    Requires current password for verification
    """
    from app.core.security import verify_password, hash_password
    from app.utils.validators import validate_password_strength

    # OAuth-only users cannot change password
    if current_user.hashed_password is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth users cannot change password"
        )

    # Verify current password
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    # Validate new password strength
    is_valid, error_message = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Ensure new password is different
    if verify_password(new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )

    # Update password
    current_user.hashed_password = hash_password(new_password)
    db.add(current_user)
    await db.commit()

    # Send notification email
    await email_service.send_email(
        to=[current_user.email],
        subject="Password Changed",
        body="Your password has been successfully changed. If you didn't do this, contact support immediately.",
        html="<p>Your password has been successfully changed.</p><p>If you didn't do this, contact support immediately.</p>"
    )

    return {"message": "Password changed successfully"}


@router.delete("/delete-account")
async def delete_account(
    password: str = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete current user's account (GDPR compliance)
    Requires password confirmation for security.
    OAuth users must confirm with 'DELETE' string instead.
    """
    from app.core.security import verify_password

    # For OAuth users, require typing 'DELETE' as confirmation
    if current_user.hashed_password is None:
        if password != "DELETE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth users must type 'DELETE' to confirm account deletion"
            )
    else:
        # Verify password for regular users
        if not verify_password(password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password"
            )

    # Store email for confirmation before deletion
    user_email = current_user.email
    user_username = current_user.username

    # Delete the user
    await db.delete(current_user)
    await db.commit()

    # Send confirmation email
    await email_service.send_email(
        to=[user_email],
        subject="Account Deleted",
        body=f"Your account ({user_username}) has been permanently deleted. We're sorry to see you go.",
        html=f"<p>Your account ({user_username}) has been permanently deleted.</p><p>We're sorry to see you go.</p>"
    )

    return {"message": "Account deleted successfully"}


# Session management endpoints
@router.get("/sessions")
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    List all active sessions for the current user
    """
    from app.services.session_service import session_service

    # Get current token to mark current session
    auth_header = request.headers.get("Authorization", "")
    current_token = auth_header[7:] if auth_header.startswith("Bearer ") else None

    sessions = await session_service.get_user_sessions(
        current_user.id,
        current_token=current_token
    )

    return {
        "sessions": [s.to_dict() for s in sessions],
        "total": len(sessions)
    }


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Revoke a specific session
    """
    from app.services.session_service import session_service

    success = await session_service.revoke_session(current_user.id, session_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return {"message": "Session revoked successfully"}


@router.delete("/sessions")
async def revoke_all_sessions(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Revoke all sessions except the current one
    """
    from app.services.session_service import session_service

    # Get current token to keep current session
    auth_header = request.headers.get("Authorization", "")
    current_token = auth_header[7:] if auth_header.startswith("Bearer ") else None

    revoked_count = await session_service.revoke_all_sessions(
        current_user.id,
        except_current=current_token
    )

    return {
        "message": f"Revoked {revoked_count} session(s)",
        "revoked_count": revoked_count
    }


# TOTP (Authenticator App) endpoints
@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Begin TOTP setup - generates secret and QR code for authenticator app

    The user must scan the QR code with their authenticator app (Google Authenticator,
    Microsoft Authenticator, Authy, etc.) and then verify with a code to complete setup.

    NOTE: TOTP is NOT enabled until the user verifies with /totp/verify-setup
    """
    from app.services.totp_service import totp_service

    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is already enabled. Disable it first to set up a new authenticator."
        )

    # Check if email is verified
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please verify your email before enabling TOTP"
        )

    # Generate new TOTP secret and QR code
    secret, qr_code, provisioning_uri = totp_service.setup_totp(
        email=current_user.email,
        username=current_user.username
    )

    # Store the secret temporarily in cache until verified
    # (Don't save to DB until user confirms it works)
    await cache_set(
        f"totp_setup:{current_user.id}",
        secret,
        ttl=600  # 10 minutes to complete setup
    )

    return TOTPSetupResponse(
        secret=secret,
        qr_code=qr_code,
        provisioning_uri=provisioning_uri,
        message="Scan the QR code with your authenticator app, then verify with a code"
    )


@router.post("/totp/verify-setup")
async def verify_totp_setup(
    request: TOTPVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_endpoint(max_requests=10, window_seconds=60))
):
    """
    Complete TOTP setup by verifying a code from the authenticator app

    This confirms the user has successfully added the secret to their authenticator
    and enables TOTP for their account.
    Rate limited: 10 requests per minute per IP
    """
    from app.services.totp_service import totp_service

    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is already enabled"
        )

    # Get the pending secret from cache
    secret = await cache_get(f"totp_setup:{current_user.id}")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No TOTP setup in progress. Please start setup first with /totp/setup"
        )

    # Verify the code
    if not totp_service.verify_code(secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid code. Please try again with a fresh code from your authenticator app."
        )

    # Code verified - save secret and enable TOTP
    current_user.totp_secret = secret
    current_user.totp_enabled = True
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    # Clean up the setup cache
    await cache_delete(f"totp_setup:{current_user.id}")

    # Send confirmation email
    await email_service.send_email(
        to=[current_user.email],
        subject="Authenticator App Enabled",
        body="Two-factor authentication via authenticator app has been enabled for your account.",
        html="<p>Two-factor authentication via authenticator app has been successfully enabled for your account.</p>"
    )

    return {
        "message": "TOTP has been enabled successfully",
        "totp_enabled": True
    }


@router.post("/totp/disable")
async def disable_totp(
    request: TOTPDisableRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disable TOTP authenticator

    Requires either password OR current TOTP code for security.
    OAuth-only users must provide TOTP code.
    """
    from app.services.totp_service import totp_service
    from app.core.security import verify_password

    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is not enabled"
        )

    # Validate that at least one verification method is provided
    if not request.password and not request.totp_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either password or TOTP code is required"
        )

    verified = False

    # Try password verification first (if user has password and provided one)
    if request.password and current_user.hashed_password:
        if verify_password(request.password, current_user.hashed_password):
            verified = True

    # Try TOTP verification
    if not verified and request.totp_code:
        if totp_service.verify_code(current_user.totp_secret, request.totp_code):
            verified = True

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password or TOTP code"
        )

    # Disable TOTP
    current_user.totp_secret = None
    current_user.totp_enabled = False
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    # Send notification email
    await email_service.send_email(
        to=[current_user.email],
        subject="Authenticator App Disabled",
        body="Two-factor authentication via authenticator app has been disabled for your account. If this wasn't you, please secure your account immediately.",
        html="<p>Two-factor authentication via authenticator app has been disabled for your account.</p><p>If this wasn't you, please secure your account immediately.</p>"
    )

    return {
        "message": "TOTP has been disabled successfully",
        "totp_enabled": False
    }


@router.post("/totp/verify", response_model=Token)
async def verify_totp_login(
    request: TwoFactorRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_endpoint(max_requests=10, window_seconds=60))
):
    """
    Verify TOTP code during login and complete authentication

    This is used when a user with TOTP enabled logs in.
    Rate limited: 10 requests per minute per IP
    """
    from app.services.totp_service import totp_service
    from app.core.security import create_access_token, create_refresh_token
    from datetime import datetime, timezone

    # Get user_id from session token
    user_id_str = await cache_get(f"totp_login:{request.session_token}")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please login again."
        )

    user_id = int(user_id_str)

    # Get user
    user = await user_crud.get(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Verify TOTP code
    if not totp_service.verify_code(user.totp_secret, request.code):
        # Track failed attempts for brute-force protection
        fail_key = f"totp_fail:{user_id}"
        fail_count = await cache_get(fail_key)
        fail_count = int(fail_count) + 1 if fail_count else 1
        await cache_set(fail_key, str(fail_count), ttl=300)  # 5 minute window

        if fail_count >= 5:
            # Delete the session to force re-login
            await cache_delete(f"totp_login:{request.session_token}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Too many failed attempts. Please login again."
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code"
        )

    # Clear failed attempts and session token
    await cache_delete(f"totp_fail:{user_id}")
    await cache_delete(f"totp_login:{request.session_token}")

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()

    # Generate tokens
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        }
    )
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        }
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
