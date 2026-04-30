import httpx
from loguru import logger
from src.core.config import settings

_ai_client: httpx.AsyncClient | None = None


def get_ai_client() -> httpx.AsyncClient:
    """Return a lazily-created shared AI httpx client."""

    global _ai_client

    if _ai_client is None or _ai_client.is_closed:
        _ai_client = httpx.AsyncClient(
            base_url=settings.AI_URL,
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={"Authorization": f"Bearer {settings.SERVICE_TOKEN}"},
        )
        logger.info(f"AI httpx client created for {settings.AI_URL}")

    return _ai_client


async def aclose_ai_client() -> None:
    """Close shared AI client if it exists."""

    global _ai_client
    client = _ai_client

    if client is None:
        return

    try:
        await client.aclose()
        logger.info("AI httpx client closed")

    finally:
        _ai_client = None
