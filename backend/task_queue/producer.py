"""Redis connection for task queue (producer side)."""

from typing import Optional

import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError

from configs.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_redis: Optional[aioredis.Redis] = None
_redis_available: bool = False


async def init_redis() -> bool:
    """
    Open Redis connection pool when REDIS_ENABLED=true.
    Returns True if connected, False if skipped or unreachable.
    """
    global _redis, _redis_available

    if not settings.REDIS_ENABLED:
        logger.info("Redis disabled (REDIS_ENABLED=false) — queue features unavailable")
        _redis_available = False
        return False

    try:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=3,
        )
        await _redis.ping()
        _redis_available = True
        logger.info("Redis connection initialized")
        return True
    except (RedisConnectionError, OSError) as exc:
        logger.warning(
            "Redis unavailable (%s) — API will run without queue. "
            "Start Redis or set REDIS_ENABLED=false in .env",
            exc,
        )
        _redis = None
        _redis_available = False
        return False


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis, _redis_available
    if _redis is not None:
        await _redis.aclose()
        logger.info("Redis connection closed")
    _redis = None
    _redis_available = False


def is_redis_available() -> bool:
    return _redis_available


def get_redis() -> aioredis.Redis:
    """Return active Redis client."""
    if not _redis_available or _redis is None:
        raise RuntimeError(
            "Redis is not available. Set REDIS_ENABLED=true and start Redis, "
            "or use features that do not require the task queue."
        )
    return _redis


async def enqueue_task(queue_key: str, payload: str) -> None:
    """Push a serialized task onto a Redis list."""
    redis = get_redis()
    await redis.lpush(queue_key, payload)
    logger.debug("Enqueued task on %s", queue_key)
