import os

import httpx
import pytest

# AI Service URL — внутри Docker: http://ai-nlv-search:8501
# Локально: http://localhost:8501 (или AI_PORT из .env)
AI_URL = os.environ.get("AI_URL", "http://localhost:8501")
SERVICE_TOKEN = os.environ.get("SERVICE_TOKEN", "service-token")


@pytest.fixture
async def ai_client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(
        base_url=AI_URL,
        headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
        timeout=60.0,
    ) as c:
        yield c
