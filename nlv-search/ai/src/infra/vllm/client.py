import httpx
from src.core.config import settings

vllm_client = httpx.AsyncClient(
    base_url=settings.VLLM_URL,
    timeout=httpx.Timeout(120.0, connect=10.0),
    headers={"Authorization": f"Bearer {settings.VLLM_API_KEY}"},
)
