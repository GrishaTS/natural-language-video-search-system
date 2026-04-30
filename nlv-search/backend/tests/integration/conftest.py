import asyncio
import os
import uuid
from pathlib import Path

import httpx
import pytest

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:27367")


@pytest.fixture(scope="session")
def backend_url() -> str:
    return BACKEND_URL


@pytest.fixture(scope="session")
def platonova_20b_channel_ids() -> list[int]:
    """Динамически получает resource_id каналов для 'Платонова 20б' через VMS.

    Session-scoped: один запрос на тестовую сессию.
    Заменяет хардкоженный _PLATONOVA_20B_CHANNEL_IDS в тестах.
    """
    return asyncio.run(_fetch_channel_ids(["Платонова 20б"]))


async def _fetch_channel_ids(addresses: list[str]) -> list[int]:
    """Fetch and sort resource_ids for a list of VMS address strings.

    Tests run these lookups via `asyncio.run()` during fixture setup. Using the
    production singleton VMS client here leaks an `httpx.AsyncClient` bound to
    a loop that is immediately closed, which later surfaces as
    "Event loop is closed". Keep the lookup fully isolated inside the temporary
    fixture loop.
    """
    from src.infra.vms.api import VmsAPI
    from src.infra.vms.client import VmsClient
    from src.services.conversational_search.usecases.vms_search import VmsSearchService

    client = VmsClient()
    try:
        service = VmsSearchService(vms_api=VmsAPI(client=client))
        channels = await service.get_channels_by_addresses(addresses)
        return sorted(ch["resource_id"] for ch in channels if ch.get("resource_id") is not None)
    finally:
        await client.aclose()


@pytest.fixture(scope="session")
def platonova_20b_k1_k2_channel_ids(platonova_20b_channel_ids: list[int]) -> list[int]:
    """Channel IDs for Платонова 20Б к1 and к2 (exact VMS addresses with corpus)."""
    ids = asyncio.run(_fetch_channel_ids([
        "Беларусь, Минск, Первомайский район, Малявщина, улица Платонова, 20Б к1",
        "Беларусь, Минск, Первомайский район, Малявщина, улица Платонова, 20Б к2",
    ]))
    assert 0 < len(ids) < len(platonova_20b_channel_ids), (
        f"к1+к2 ids={len(ids)}, whole building ids={len(platonova_20b_channel_ids)} — "
        "type-filter may be broken"
    )
    return ids


@pytest.fixture(scope="session")
def platonova_20b_k1_channel_ids(platonova_20b_channel_ids: list[int]) -> list[int]:
    """Channel IDs for Платонова 20Б к1 (exact VMS address with corpus)."""
    ids = asyncio.run(_fetch_channel_ids([
        "Беларусь, Минск, Первомайский район, Малявщина, улица Платонова, 20Б к1",
    ]))
    assert 0 < len(ids) < len(platonova_20b_channel_ids), (
        f"к1 ids={len(ids)}, whole building ids={len(platonova_20b_channel_ids)} — "
        "type-filter may be broken"
    )
    return ids


@pytest.fixture(scope="session")
def platonova_20b_k1_k2_k3_channel_ids() -> list[int]:
    """Channel IDs for Платонова 20Б к1, к2, к3 (exact VMS addresses with corpus)."""
    return asyncio.run(_fetch_channel_ids([
        "Беларусь, Минск, Первомайский район, Малявщина, улица Платонова, 20Б к1",
        "Беларусь, Минск, Первомайский район, Малявщина, улица Платонова, 20Б к2",
        "Беларусь, Минск, Первомайский район, Малявщина, улица Платонова, 20Б к3",
    ]))


@pytest.fixture(scope="session")
def face_image() -> bytes:
    """Реальная PNG из MinIO (636x718, face Германа Петрова).
    Используется в photo-тестах для извлечения face-дескриптора через VMS."""
    path = Path(__file__).parent / "fixtures" / "face.png"
    return path.read_bytes()


@pytest.fixture
async def client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30.0) as c:
        yield c


@pytest.fixture
async def auth_headers(client: httpx.AsyncClient) -> dict:
    """Регистрирует уникального тестового пользователя, возвращает Authorization header.
    После теста удаляет пользователя через DELETE /auth/me."""
    suffix = uuid.uuid4().hex[:8]
    username = f"testuser_{suffix}"
    email = f"{username}@example.com"
    password = "Test1234!"

    resp = await client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
    })
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    yield headers

    await client.delete("/auth/me", headers=headers)
