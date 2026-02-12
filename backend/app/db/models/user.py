"""
User database model
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text
from sqlalchemy.sql import func

from app.core.async_database import Base
from app.db.models.enums import UserRole


class User(Base):
    """
    User model for authentication and user management
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)

    # OAuth fields
    oauth_provider = Column(String(50), nullable=True)  # 'google', 'github', etc.
    oauth_id = Column(String(255), nullable=True)  # Provider's user ID

    # Stripe fields
    stripe_customer_id = Column(String(255), nullable=True)  # Stripe customer ID
    stripe_connect_id = Column(String(255), nullable=True)  # Stripe Connect account ID

    # Contact & Profile
    phone_number = Column(String(20), nullable=True)
    phone_verified = Column(Boolean, default=False)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)

    # Settings & Preferences
    timezone = Column(String(50), nullable=True, default="UTC")
    language = Column(String(10), nullable=True, default="en")

    # Status & Security
    is_active = Column(Boolean, default=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    email_verified = Column(Boolean, default=False)

    # Two-Factor Authentication
    two_fa_enabled = Column(Boolean, default=False)  # Email-based 2FA
    totp_secret = Column(String(32), nullable=True)  # TOTP secret for authenticator apps
    totp_enabled = Column(Boolean, default=False)    # Whether TOTP is active

    # Timestamps
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def full_name(self) -> str:
        """Get full name from first and last name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return ""

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email}, role={self.role})>"
