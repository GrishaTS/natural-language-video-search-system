import hashlib
import time
from typing import Dict

from loguru import logger
from src.infra.redis.database import redis_client

_memory_blacklist: Dict[str, float] = {}

_memory_only = False


def _cleanup_memory(now: float) -> None:
    """Remove expired entries from the in-memory blacklist fallback."""

    expired = [key for key, expires in _memory_blacklist.items() if expires <= now]

    for key in expired:
        _memory_blacklist.pop(key, None)


def _hash_token(token: str) -> str:
    """Return a SHA-256 hex digest of the token for storage."""

    return hashlib.sha256(token.encode()).hexdigest()


async def blacklist_token(token: str, ttl_seconds: int) -> None:
    """Add a token to the blacklist for the given TTL.

    Stores the SHA-256 hash in Redis. Falls back to an in-process dict if Redis is unavailable.

    Args:
        token: Raw JWT string.
        ttl_seconds: Seconds until the blacklist entry expires.
    """

    digest = _hash_token(token)
    now = time.monotonic()
    ttl_seconds = max(ttl_seconds, 0)
    global _memory_only

    if not _memory_only:
        try:
            await redis_client.setex(f"token:blacklist:{digest}", ttl_seconds or 1, "1")
            logger.info(f"Token blacklisted for {ttl_seconds} seconds")
            return

        except Exception:
            _memory_only = True
            logger.warning(
                "Redis unavailable for token blacklist, using in-memory store"
            )

    _cleanup_memory(now)
    _memory_blacklist[digest] = now + ttl_seconds if ttl_seconds else float("inf")


async def is_token_blacklisted(token: str) -> bool:
    """Return True if the token hash is found in the active blacklist.

    Checks Redis first and falls back to an in-memory store on Redis failure.

    Args:
        token: Raw JWT string.

    Returns:
        True if the token has been revoked, False otherwise.
    """

    digest = _hash_token(token)
    now = time.monotonic()
    _cleanup_memory(now)
    global _memory_only

    if not _memory_only:
        try:
            exists = await redis_client.exists(f"token:blacklist:{digest}")

            if exists:
                logger.warning("Rejected blacklisted token (redis)")
                return True

        except Exception:
            _memory_only = True
            logger.warning(
                "Redis unavailable when checking blacklist, falling back to memory"
            )

    expires_at = _memory_blacklist.get(digest)

    if expires_at and expires_at > now:
        logger.warning("Rejected blacklisted token (in-memory)")
        return True

    return False
