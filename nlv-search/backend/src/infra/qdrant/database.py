import inspect

from qdrant_client import AsyncQdrantClient
from src.core.config import settings

qdrant_client = AsyncQdrantClient(
    host=settings.QDRANT_HOST,
    port=settings.QDRANT_PORT,
    api_key=settings.QDRANT_API_KEY or None,
    https=settings.QDRANT_HTTPS,
    timeout=30.0,
)


async def close_qdrant_client() -> None:
    """Close the shared Qdrant client, handling both coroutine and sync close methods."""

    close = getattr(qdrant_client, "close", None)

    if callable(close):
        result = close()

        if inspect.iscoroutine(result):
            await result
