"""
Async Database Configuration and Session Management
"""
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
import ssl

from app.core.config import settings


def get_database_url():
    """
    Process DATABASE_URL and handle SSL parameters for asyncpg
    """
    url = settings.DATABASE_URL

    # Remove sslmode parameter from URL if present (asyncpg doesn't support it)
    if "?" in url:
        base_url, params = url.split("?", 1)
        # Filter out sslmode parameter
        params_list = [p for p in params.split("&") if not p.startswith("sslmode=")]
        if params_list:
            url = f"{base_url}?{'&'.join(params_list)}"
        else:
            url = base_url

    return url


# Create async engine with SSL support for asyncpg
engine_kwargs = {
    "echo": settings.DB_ECHO,
    "pool_size": settings.DB_POOL_SIZE,
    "max_overflow": settings.DB_MAX_OVERFLOW,
    "pool_pre_ping": True,
}

# Add SSL configuration for asyncpg if sslmode was in the URL
if "sslmode=require" in settings.DATABASE_URL or "ssl=" in settings.DATABASE_URL:
    # Create SSL context for asyncpg
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    engine_kwargs["connect_args"] = {
        "ssl": ssl_context,
        "server_settings": {
            "application_name": settings.PROJECT_NAME
        }
    }

engine = create_async_engine(
    get_database_url(),
    **engine_kwargs
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """
    Base class for all database models
    """
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables
    """
    async with engine.begin() as conn:
        # Import all models here to ensure they are registered with Base
        # from app.db.models import user, item  # Example

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized")


async def close_db() -> None:
    """
    Close database connections
    """
    await engine.dispose()
    print("Database connections closed")
