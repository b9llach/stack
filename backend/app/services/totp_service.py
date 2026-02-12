"""
TOTP (Time-based One-Time Password) service for authenticator app support.

Supports Google Authenticator, Microsoft Authenticator, Authy, etc.
"""
import pyotp
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64
import logging
from typing import Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


class TOTPService:
    """
    Service for TOTP authentication (Google Authenticator, etc.)
    """

    def __init__(self):
        self.issuer = settings.PROJECT_NAME
        # TOTP settings
        self.digits = 6  # Standard 6-digit codes
        self.interval = 30  # Standard 30-second interval

    def generate_secret(self) -> str:
        """
        Generate a new TOTP secret.

        Returns:
            Base32-encoded secret string (32 characters)
        """
        return pyotp.random_base32()

    def get_totp(self, secret: str) -> pyotp.TOTP:
        """
        Get a TOTP object for the given secret.

        Args:
            secret: Base32-encoded secret

        Returns:
            pyotp.TOTP object
        """
        return pyotp.TOTP(
            secret,
            digits=self.digits,
            interval=self.interval,
            issuer=self.issuer
        )

    def generate_provisioning_uri(
        self,
        secret: str,
        email: str,
        username: Optional[str] = None
    ) -> str:
        """
        Generate the provisioning URI for QR code.

        This is the otpauth:// URI that authenticator apps scan.

        Args:
            secret: Base32-encoded secret
            email: User's email
            username: Optional username to display

        Returns:
            otpauth:// URI string
        """
        totp = self.get_totp(secret)
        # Use username if provided, otherwise email
        account_name = username or email
        return totp.provisioning_uri(name=account_name, issuer_name=self.issuer)

    def generate_qr_code_base64(
        self,
        secret: str,
        email: str,
        username: Optional[str] = None
    ) -> str:
        """
        Generate a QR code as a base64-encoded PNG image.

        Args:
            secret: Base32-encoded secret
            email: User's email
            username: Optional username

        Returns:
            Base64-encoded PNG image string (data URI format)
        """
        uri = self.generate_provisioning_uri(secret, email, username)

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return f"data:image/png;base64,{img_base64}"

    def generate_qr_code_svg(
        self,
        secret: str,
        email: str,
        username: Optional[str] = None
    ) -> str:
        """
        Generate a QR code as an SVG string.

        Args:
            secret: Base32-encoded secret
            email: User's email
            username: Optional username

        Returns:
            SVG string
        """
        uri = self.generate_provisioning_uri(secret, email, username)

        # Generate QR code as SVG
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        # Create SVG image
        factory = qrcode.image.svg.SvgImage
        img = qr.make_image(image_factory=factory)

        # Convert to string
        buffer = BytesIO()
        img.save(buffer)
        buffer.seek(0)
        return buffer.getvalue().decode("utf-8")

    def verify_code(self, secret: str, code: str, window: int = 1) -> bool:
        """
        Verify a TOTP code.

        Args:
            secret: Base32-encoded secret
            code: 6-digit code from authenticator app
            window: Number of time windows to check (for clock drift)
                   1 = current + 1 previous + 1 next (90 second total window)

        Returns:
            True if code is valid
        """
        if not secret or not code:
            return False

        # Clean the code (remove spaces, etc.)
        code = code.strip().replace(" ", "").replace("-", "")

        # Verify it's a 6-digit numeric code
        if not code.isdigit() or len(code) != 6:
            return False

        totp = self.get_totp(secret)

        # verify_otp returns True/False, valid_window allows for clock drift
        return totp.verify(code, valid_window=window)

    def get_current_code(self, secret: str) -> str:
        """
        Get the current TOTP code (for testing purposes).

        Args:
            secret: Base32-encoded secret

        Returns:
            Current 6-digit code
        """
        totp = self.get_totp(secret)
        return totp.now()

    def setup_totp(
        self,
        email: str,
        username: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Generate everything needed for TOTP setup.

        Args:
            email: User's email
            username: Optional username

        Returns:
            Tuple of (secret, qr_code_base64, provisioning_uri)
        """
        secret = self.generate_secret()
        qr_code = self.generate_qr_code_base64(secret, email, username)
        uri = self.generate_provisioning_uri(secret, email, username)

        return secret, qr_code, uri


# Singleton instance
totp_service = TOTPService()
