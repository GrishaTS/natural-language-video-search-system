from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import jwt
from src.core.auth import TokenPayload
from src.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the bcrypt hash."""

    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )

    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    """Return a bcrypt hash of the given password."""

    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token for the given subject.

    Args:
        subject: Value to store in the ``sub`` claim, typically a user UUID.
        expires_delta: Token lifetime; defaults to ``AUTH_ACCESS_TOKEN_EXPIRE_MINUTES``.

    Returns:
        Encoded JWT string.
    """

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode: dict[str, Any] = {"exp": expire, "sub": subject}
    return jwt.encode(
        to_encode, settings.AUTH_SECRET_KEY, algorithm=settings.AUTH_ALGORITHM
    )


def decode_access_token(token: str) -> TokenPayload:
    """Decode and verify a JWT, returning its payload.

    Args:
        token: Raw JWT string.

    Returns:
        TokenPayload with ``sub`` and ``exp`` fields.

    Raises:
        jose.JWTError: If the token is invalid or expired.
    """

    payload = jwt.decode(
        token,
        settings.AUTH_SECRET_KEY,
        algorithms=[settings.AUTH_ALGORITHM],
    )
    return TokenPayload(sub=payload.get("sub"), exp=payload.get("exp"))


def get_token_ttl_seconds(token: str) -> int:
    """Return remaining lifetime for the given JWT (seconds)."""

    payload = decode_access_token(token)

    if payload.exp is None:
        return settings.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60

    now = datetime.now(timezone.utc).timestamp()
    return max(int(payload.exp - now), 0)
