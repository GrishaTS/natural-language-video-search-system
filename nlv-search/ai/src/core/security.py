import secrets

from src.core.config import settings


def verify_service_token(token: str) -> bool:
    """Return True if the token matches the configured SERVICE_TOKEN."""

    return secrets.compare_digest(token, settings.SERVICE_TOKEN)
