import redis.asyncio as redis
from src.core.config import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=False,
)


async def close_redis_client() -> None:
    """Close the shared Redis connection pool."""

    close = getattr(redis_client, "aclose", None)

    if callable(close):
        await close()
        return

    await redis_client.connection_pool.disconnect(inuse_connections=True)
