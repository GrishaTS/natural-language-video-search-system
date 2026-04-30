import httpx
from src.core.config import settings

tei_client = httpx.AsyncClient(
    base_url=settings.TEI_URL,
    timeout=httpx.Timeout(30.0, connect=5.0),
)
