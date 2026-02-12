"""
Security Headers Middleware

Adds security headers to all responses to protect against common web vulnerabilities.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: Basic XSS protection (legacy browsers)
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features
    - Content-Security-Policy: Controls resource loading (configurable)
    - Strict-Transport-Security: Forces HTTPS (production only)
    """

    def __init__(self, app):
        super().__init__(app)

        # Base security headers (always applied)
        self.security_headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",

            # Prevent clickjacking
            "X-Frame-Options": "DENY",

            # XSS protection for legacy browsers
            "X-XSS-Protection": "1; mode=block",

            # Control referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # Disable various browser features we don't need
            "Permissions-Policy": (
                "accelerometer=(), "
                "camera=(), "
                "geolocation=(), "
                "gyroscope=(), "
                "magnetometer=(), "
                "microphone=(), "
                "payment=(), "
                "usb=()"
            ),

            # Cache control for API responses
            "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }

        # HSTS header (only in production with HTTPS)
        if not settings.DEBUG:
            # 1 year HSTS, include subdomains, allow preload
            self.security_headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy
        # Customize based on your needs
        self.security_headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Needed for Swagger UI
            "style-src 'self' 'unsafe-inline'; "  # Needed for Swagger UI
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers
        for header, value in self.security_headers.items():
            # Don't override if already set
            if header not in response.headers:
                response.headers[header] = value

        return response
