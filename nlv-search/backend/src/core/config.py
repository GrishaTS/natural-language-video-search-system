from datetime import timedelta

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and the .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    PROJECT_NAME: str = "Natural Language Video Search System"
    VERSION: str
    BACKEND_HOST: str
    BACKEND_PORT: int
    BACKEND_LOG_LEVEL: str
    BACKEND_CORS_ORIGINS: list[str]
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    MINIO_HOST: str
    MINIO_API_PORT: int
    MINIO_BUCKET: str
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    QDRANT_HOST: str
    QDRANT_PORT: int
    QDRANT_API_KEY: str
    QDRANT_HTTPS: bool = False
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str
    AI_HOST: str
    AI_PORT: int
    AUTH_SECRET_KEY: str
    AUTH_ALGORITHM: str
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int
    SERVICE_TOKEN: str
    VMS_API_URL: str
    VMS_BEARER_TOKEN: str
    VMS_USERNAME: str
    VMS_PASSWORD: str
    VMS_FRONTEND_URL: str
    NLV_BOT_USERNAME: str = ""
    NLV_BOT_PASSWORD: str = ""
    DEFAULT_USER_PASSWORD: str

    @computed_field
    @property
    def POSTGRES_URL(self) -> str:
        """SQLAlchemy async PostgreSQL connection URL."""

        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def POSTGRES_URL_PSYCOPG(self) -> str:
        """Psycopg3 synchronous PostgreSQL connection URL for LangGraph checkpointer."""

        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def auth_access_token_timedelta(self) -> timedelta:
        """Access token lifetime as a timedelta object."""

        return timedelta(minutes=self.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES)

    @computed_field
    @property
    def MINIO_ENDPOINT(self) -> str:
        """MinIO host:port endpoint string."""

        return f"{self.MINIO_HOST}:{self.MINIO_API_PORT}"

    @computed_field
    @property
    def AI_URL(self) -> str:
        """AI service base URL with scheme, host, and port."""

        return f"http://{self.AI_HOST}:{self.AI_PORT}"


settings = Settings()
