"""
Health check endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.async_database import get_db
from app.core.cache import get_redis

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint
    """
    return {
        "status": "healthy",
        "message": "Service is running"
    }


@router.get("/health/db")
async def database_health(db: AsyncSession = Depends(get_db)):
    """
    Check database connectivity
    """
    try:
        # Execute a simple query
        await db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


@router.get("/health/cache")
async def cache_health():
    """
    Check Redis cache connectivity
    """
    try:
        redis = await get_redis()
        await redis.ping()
        return {
            "status": "healthy",
            "cache": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "cache": "disconnected",
            "error": str(e)
        }
