import httpx
from src.core.config import settings

openrouter_client = httpx.AsyncClient(
    base_url=settings.OPENROUTER_URL,
    timeout=httpx.Timeout(120.0, connect=10.0),
    headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
)
