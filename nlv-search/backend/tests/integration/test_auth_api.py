import uuid

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def user_creds() -> dict:
    uid = uuid.uuid4().hex[:8]
    return {
        "username": f"authtest_{uid}",
        "email": f"authtest_{uid}@example.com",
        "password": "SecurePass123!",
    }


async def test_register_returns_token(client: httpx.AsyncClient, user_creds: dict):
    resp = await client.post("/auth/register", json=user_creds)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["username"] == user_creds["username"]


async def test_login_returns_token(client: httpx.AsyncClient, user_creds: dict):
    await client.post("/auth/register", json=user_creds)
    resp = await client.post("/auth/login", data={
        "username": user_creds["username"],
        "password": user_creds["password"],
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password_returns_401(client: httpx.AsyncClient, user_creds: dict):
    await client.post("/auth/register", json=user_creds)
    resp = await client.post("/auth/login", data={
        "username": user_creds["username"],
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


async def test_me_returns_current_user(client: httpx.AsyncClient, user_creds: dict):
    reg = await client.post("/auth/register", json=user_creds)
    token = reg.json()["access_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == user_creds["username"]


async def test_logout_then_me_returns_401(client: httpx.AsyncClient, user_creds: dict):
    reg = await client.post("/auth/register", json=user_creds)
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    logout = await client.post("/auth/logout", headers=headers)
    assert logout.status_code == 204

    me = await client.get("/auth/me", headers=headers)
    assert me.status_code == 401


async def test_duplicate_register_returns_400(client: httpx.AsyncClient, user_creds: dict):
    await client.post("/auth/register", json=user_creds)
    resp = await client.post("/auth/register", json=user_creds)
    assert resp.status_code == 400


async def test_unauthenticated_request_returns_401(client: httpx.AsyncClient):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
