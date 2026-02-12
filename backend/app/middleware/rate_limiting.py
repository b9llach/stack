"""
Rate Limiting Middleware with Redis support for distributed deployments
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis for distributed rate limiting.

    Uses a sliding window algorithm with Redis INCR and EXPIRE for atomic operations.
    Falls back to allowing requests if Redis is unavailable (fail-open).
    """

    def __init__(self, app):
        super().__init__(app)
        self.rate_limit = settings.RATE_LIMIT_PER_MINUTE
        self.window = 60  # 60 seconds window

        # Paths to skip rate limiting
        self.skip_paths = {
            "/",
            "/api/v1/health",
            "/api/v1/health/db",
            "/api/v1/health/cache",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
        }

    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP, checking for proxy headers.
        """
        # Check for forwarded header (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain (original client)
            return forwarded.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct connection IP
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        """
        Process request and check rate limit using Redis.
        """
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip rate limiting for health checks and docs
        if request.url.path in self.skip_paths:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        current_time = int(time.time())

        # Use minute-based key for sliding window
        window_key = current_time // self.window
        redis_key = f"ratelimit:{client_ip}:{window_key}"

        try:
            from app.core.cache import get_redis

            redis = await get_redis()

            # Atomic increment and get
            pipe = redis.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, self.window + 1)  # Extra second for safety
            results = await pipe.execute()

            request_count = results[0]

            if request_count > self.rate_limit:
                retry_after = self.window - (current_time % self.window)
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Please try again later.",
                        "rate_limit": self.rate_limit,
                        "window": f"{self.window}s",
                        "retry_after": retry_after
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.rate_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(current_time + retry_after)
                    }
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            remaining = max(0, self.rate_limit - request_count)
            reset_time = (window_key + 1) * self.window

            response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)

            return response

        except Exception as e:
            # Fail open - if Redis is down, allow the request
            # Log the error for monitoring
            logger.warning(f"Rate limiting failed (allowing request): {e}")
            return await call_next(request)
