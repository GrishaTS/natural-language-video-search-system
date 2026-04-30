import httpx
import pytest

pytestmark = pytest.mark.integration


async def test_health_returns_200(ai_client: httpx.AsyncClient):
    resp = await ai_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


async def test_embed_single_returns_vector_768(ai_client: httpx.AsyncClient):
    resp = await ai_client.post("/embed/text", json={"texts": ["Иван Петров"]})
    assert resp.status_code == 200
    data = resp.json()
    embeddings = data["embeddings"]
    assert len(embeddings) == 1
    vector = embeddings[0]
    assert len(vector) == 768
    assert all(isinstance(v, float) for v in vector)


async def test_embed_batch_returns_two_vectors(ai_client: httpx.AsyncClient):
    resp = await ai_client.post("/embed/text", json={"texts": ["Петров Иван", "Сидоров Алексей"]})
    assert resp.status_code == 200
    data = resp.json()
    embeddings = data["embeddings"]
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 768
    assert len(embeddings[1]) == 768


async def test_embed_without_auth_returns_401():
    async with httpx.AsyncClient(
        base_url=__import__("os").environ.get("AI_URL", "http://localhost:8501"),
        timeout=10.0,
    ) as c:
        resp = await c.post("/embed/text", json={"texts": ["test"]})
    assert resp.status_code == 401


async def test_chat_completions_non_streaming(ai_client: httpx.AsyncClient):
    resp = await ai_client.post("/v1/chat/completions", json={
        "model": "default",
        "messages": [{"role": "user", "content": "Скажи только слово 'ok'"}],
        "max_tokens": 20,
        "stream": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "choices" in data
    assert len(data["choices"]) > 0
    content = data["choices"][0]["message"]["content"]
    assert isinstance(content, str)
    assert len(content) > 0
