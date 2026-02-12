"""
Google OAuth utilities
"""
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status
from typing import Dict, Any

from app.core.config import settings


# Initialize OAuth
oauth = OAuth()


def configure_google_oauth():
    """
    Configure Google OAuth client

    Call this during application startup if Google OAuth is enabled
    """
    if not settings.GOOGLE_OAUTH_ENABLED:
        return

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ValueError(
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set when GOOGLE_OAUTH_ENABLED is True"
        )

    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )


def validate_google_user_info(user_info: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate and extract required fields from Google user info

    Args:
        user_info: User info from Google OAuth

    Returns:
        Dictionary with validated user data

    Raises:
        HTTPException: If required fields are missing
    """
    email = user_info.get('email')
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by Google"
        )

    if not user_info.get('email_verified', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google email not verified"
        )

    # Extract user data
    given_name = user_info.get('given_name', '')
    family_name = user_info.get('family_name', '')
    picture = user_info.get('picture', '')

    # Generate username from email if not provided
    # Google doesn't provide username, so we create one from email
    username = email.split('@')[0]

    return {
        'email': email,
        'username': username,
        'first_name': given_name,
        'last_name': family_name,
        'avatar_url': picture,
        'email_verified': True,
        'oauth_provider': 'google',
        'oauth_id': user_info.get('sub', '')  # Google's user ID
    }
