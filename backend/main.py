"""
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.async_database import init_db, close_db
from app.core.cache import init_cache, close_cache
from app.core.sentry import init_sentry
from app.core.exceptions import setup_exception_handlers
from app.api.routers import health, users, auth, stripe, files, notifications
from app.middleware.rate_limiting import RateLimitMiddleware
from app.middleware.correlation_id import CorrelationIDMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.websockets import router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Setup logging first
    from app.utils.logger import setup_logging
    setup_logging(
        log_level="DEBUG" if settings.DEBUG else "INFO",
        json_logs=not settings.DEBUG
    )

    # Startup
    await init_db()
    await init_cache()

    # Initialize Sentry
    init_sentry()

    # Configure Google OAuth if enabled
    if settings.GOOGLE_OAUTH_ENABLED:
        from app.core.oauth import configure_google_oauth
        configure_google_oauth()
        print("Google OAuth configured")

    print("Application startup complete")

    yield

    # Shutdown
    await close_db()
    await close_cache()
    print("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Setup global exception handlers
setup_exception_handlers(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add correlation ID middleware (for request tracing)
app.add_middleware(CorrelationIDMiddleware)

# Add session middleware (required for OAuth)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Include routers
app.include_router(health.router, prefix=f"{settings.API_PREFIX}/health", tags=["Health"])
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_PREFIX}/users", tags=["Users"])
app.include_router(stripe.router, prefix=f"{settings.API_PREFIX}/stripe", tags=["Stripe"])
app.include_router(files.router, prefix=f"{settings.API_PREFIX}/files", tags=["Files"])
app.include_router(notifications.router, prefix=f"{settings.API_PREFIX}/notifications", tags=["Notifications"])
app.include_router(websocket_router.router, tags=["WebSocket"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to FastAPI Template",
        "docs": "/api/docs",
        "version": settings.VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
