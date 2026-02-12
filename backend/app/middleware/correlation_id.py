"""
Correlation ID middleware for request tracing with structured logging
"""
import uuid
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.utils.logger import context_filter

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Add correlation ID to each request for tracing.
    Also logs request/response with timing information.
    """

    # Paths to skip detailed logging
    SKIP_PATHS = {"/", "/api/docs", "/api/redoc", "/api/openapi.json", "/api/v1/health"}

    async def dispatch(self, request: Request, call_next):
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        # Store in request state
        request.state.correlation_id = correlation_id

        # Get client IP
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.headers.get("X-Real-IP", "")
        if not client_ip and request.client:
            client_ip = request.client.host

        # Set logging context
        context_filter.set_context(
            request_id=correlation_id,
            client_ip=client_ip,
            method=request.method,
            endpoint=request.url.path
        )

        # Start timing
        start_time = time.perf_counter()

        # Log request (skip health checks and docs)
        if request.url.path not in self.SKIP_PATHS:
            logger.info(
                f"Request started: {request.method} {request.url.path}",
                extra={
                    "request_id": correlation_id,
                    "client_ip": client_ip,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "query_params": str(request.query_params) if request.query_params else None,
                    "user_agent": request.headers.get("User-Agent", "")[:100]
                }
            )

        try:
            # Call next middleware/endpoint
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Add headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Request-Duration-Ms"] = f"{duration_ms:.2f}"

            # Log response (skip health checks and docs)
            if request.url.path not in self.SKIP_PATHS:
                log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
                logger.log(
                    log_level,
                    f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                    extra={
                        "request_id": correlation_id,
                        "status_code": response.status_code,
                        "duration_ms": round(duration_ms, 2)
                    }
                )

            return response

        except Exception as e:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log exception
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {type(e).__name__}",
                extra={
                    "request_id": correlation_id,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e)
                },
                exc_info=True
            )
            raise

        finally:
            # Clear logging context
            context_filter.clear_context()
