"""
Global exception handling and standardized error responses
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AppException(Exception):
    """
    Base application exception for custom errors
    """
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An unexpected error occurred",
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code or "INTERNAL_ERROR"
        self.headers = headers


class NotFoundError(AppException):
    """Resource not found"""
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found",
            error_code="NOT_FOUND"
        )


class ConflictError(AppException):
    """Resource conflict (duplicate)"""
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT"
        )


class UnauthorizedError(AppException):
    """Authentication required"""
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenError(AppException):
    """Access forbidden"""
    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN"
        )


class BadRequestError(AppException):
    """Bad request"""
    def __init__(self, detail: str = "Bad request"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="BAD_REQUEST"
        )


class RateLimitError(AppException):
    """Rate limit exceeded"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            error_code="RATE_LIMITED",
            headers={"Retry-After": str(retry_after)}
        )


def create_error_response(
    status_code: int,
    detail: str,
    error_code: str = "ERROR",
    errors: Optional[list] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create standardized error response
    """
    response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": detail
        }
    }

    if errors:
        response["error"]["details"] = errors

    if request_id:
        response["request_id"] = request_id

    return response


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Configure global exception handlers for the application
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle custom application exceptions"""
        request_id = getattr(request.state, "correlation_id", None)

        logger.warning(
            f"AppException: {exc.error_code} - {exc.detail}",
            extra={"request_id": request_id, "status_code": exc.status_code}
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=create_error_response(
                status_code=exc.status_code,
                detail=exc.detail,
                error_code=exc.error_code,
                request_id=request_id
            ),
            headers=exc.headers
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions"""
        request_id = getattr(request.state, "correlation_id", None)

        # Map status codes to error codes
        error_codes = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMITED",
            500: "INTERNAL_ERROR",
            502: "BAD_GATEWAY",
            503: "SERVICE_UNAVAILABLE",
        }

        error_code = error_codes.get(exc.status_code, "ERROR")

        return JSONResponse(
            status_code=exc.status_code,
            content=create_error_response(
                status_code=exc.status_code,
                detail=str(exc.detail),
                error_code=error_code,
                request_id=request_id
            ),
            headers=getattr(exc, "headers", None)
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors with detailed field information"""
        request_id = getattr(request.state, "correlation_id", None)

        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })

        logger.info(
            f"Validation error: {len(errors)} field(s)",
            extra={"request_id": request_id, "errors": errors}
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=create_error_response(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Validation error",
                error_code="VALIDATION_ERROR",
                errors=errors,
                request_id=request_id
            )
        )

    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(request: Request, exc: IntegrityError):
        """Handle database integrity errors (unique constraint, foreign key, etc.)"""
        request_id = getattr(request.state, "correlation_id", None)

        logger.error(
            f"Database integrity error: {str(exc)}",
            extra={"request_id": request_id}
        )

        # Parse common constraint violations
        detail = "A database constraint was violated"
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            detail = "A record with this value already exists"

        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=create_error_response(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
                error_code="CONFLICT",
                request_id=request_id
            )
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handle SQLAlchemy errors"""
        request_id = getattr(request.state, "correlation_id", None)

        logger.error(
            f"Database error: {str(exc)}",
            extra={"request_id": request_id},
            exc_info=True
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=create_error_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred",
                error_code="DATABASE_ERROR",
                request_id=request_id
            )
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions"""
        request_id = getattr(request.state, "correlation_id", None)

        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
            extra={"request_id": request_id},
            exc_info=True
        )

        # In debug mode, include exception details
        from app.core.config import settings
        if settings.DEBUG:
            detail = f"{type(exc).__name__}: {str(exc)}"
        else:
            detail = "An unexpected error occurred"

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=create_error_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=detail,
                error_code="INTERNAL_ERROR",
                request_id=request_id
            )
        )
