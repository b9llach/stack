"""
Redis Cache Configuration and Utilities
"""
from redis.asyncio import Redis
from typing import Optional, Any
import json

from app.core.config import settings


# Global Redis client
redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """
    Get Redis client instance

    Returns:
        Redis client
    """
    if redis_client is None:
        raise RuntimeError("Redis client not initialized")
    return redis_client


async def init_cache() -> None:
    """
    Initialize Redis connection
    """
    global redis_client
    redis_client = Redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )
    await redis_client.ping()
    print("Redis cache initialized")


async def close_cache() -> None:
    """
    Close Redis connection
    """
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
    print("Redis cache closed")


async def cache_get(key: str) -> Optional[Any]:
    """
    Get value from cache

    Args:
        key: Cache key

    Returns:
        Cached value or None
    """
    client = await get_redis()
    value = await client.get(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return None


async def cache_set(
    key: str,
    value: Any,
    ttl: int = settings.CACHE_TTL
) -> bool:
    """
    Set value in cache

    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds

    Returns:
        True if successful
    """
    client = await get_redis()
    if not isinstance(value, str):
        value = json.dumps(value)
    await client.setex(key, ttl, value)
    return True


async def cache_delete(key: str) -> bool:
    """
    Delete key from cache

    Args:
        key: Cache key

    Returns:
        True if key was deleted
    """
    client = await get_redis()
    result = await client.delete(key)
    return bool(result)


async def cache_clear_pattern(pattern: str) -> int:
    """
    Delete all keys matching pattern

    Args:
        pattern: Key pattern (e.g., "user:*")

    Returns:
        Number of keys deleted
    """
    client = await get_redis()
    keys = await client.keys(pattern)
    if keys:
        return await client.delete(*keys)
    return 0
