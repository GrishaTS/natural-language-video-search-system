import time
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import fakeredis.aioredis
from jose import ExpiredSignatureError

from src.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from src.infra.redis.auth_blacklist import blacklist_token, is_token_blacklisted


# ── Password hashing ──────────────────────────────────────────────────────────

def test_verify_correct_password():
    hashed = get_password_hash("mysecret")
    assert verify_password("mysecret", hashed) is True


def test_verify_wrong_password():
    hashed = get_password_hash("mysecret")
    assert verify_password("wrongpass", hashed) is False


def test_different_hashes_for_same_password():
    h1 = get_password_hash("same")
    h2 = get_password_hash("same")
    # bcrypt salts produce different hashes each time
    assert h1 != h2
    assert verify_password("same", h1)
    assert verify_password("same", h2)


# ── JWT ───────────────────────────────────────────────────────────────────────

def test_create_and_decode_token():
    token = create_access_token(subject="user-123")
    payload = decode_access_token(token)
    assert payload.sub == "user-123"
    assert payload.exp is not None
    assert payload.exp > time.time()


def test_expired_token_raises():
    token = create_access_token(subject="user-123", expires_delta=timedelta(seconds=-1))
    with pytest.raises(ExpiredSignatureError):
        decode_access_token(token)


def test_different_subjects_produce_different_tokens():
    t1 = create_access_token(subject="user-1")
    t2 = create_access_token(subject="user-2")
    assert t1 != t2
    assert decode_access_token(t1).sub == "user-1"
    assert decode_access_token(t2).sub == "user-2"


# ── Redis blacklist ───────────────────────────────────────────────────────────

@pytest.fixture
async def fake_redis_client():
    client = fakeredis.aioredis.FakeRedis()
    yield client
    await client.aclose()


async def test_blacklisted_token_is_detected(fake_redis_client):
    token = create_access_token(subject="user-blacklist")
    # Патчим модуль-уровневый redis_client в auth_blacklist
    with patch("src.infra.redis.auth_blacklist.redis_client", fake_redis_client), \
         patch("src.infra.redis.auth_blacklist._memory_only", False):
        await blacklist_token(token, ttl_seconds=60)
        result = await is_token_blacklisted(token)
    assert result is True


async def test_non_blacklisted_token_is_not_detected(fake_redis_client):
    token = create_access_token(subject="user-clean")
    with patch("src.infra.redis.auth_blacklist.redis_client", fake_redis_client), \
         patch("src.infra.redis.auth_blacklist._memory_only", False):
        result = await is_token_blacklisted(token)
    assert result is False


async def test_different_tokens_independent_blacklist(fake_redis_client):
    token_a = create_access_token(subject="user-a")
    token_b = create_access_token(subject="user-b")
    with patch("src.infra.redis.auth_blacklist.redis_client", fake_redis_client), \
         patch("src.infra.redis.auth_blacklist._memory_only", False):
        await blacklist_token(token_a, ttl_seconds=60)
        assert await is_token_blacklisted(token_a) is True
        assert await is_token_blacklisted(token_b) is False
