from pydantic import BaseModel


class TokenPayload(BaseModel):
    """Decoded JWT payload containing subject user ID and expiry."""

    sub: str | None = None
    exp: int | None = None
