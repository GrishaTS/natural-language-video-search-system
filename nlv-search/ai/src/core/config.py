from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AI service configuration loaded from environment variables and the .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    PROJECT_NAME: str = "Natural Language Video Search AI Service"
    VERSION: str
    AI_HOST: str
    AI_PORT: int
    AI_LOG_LEVEL: str
    SERVICE_TOKEN: str
    VLLM_URL: str
    VLLM_API_KEY: str
    VLLM_MODEL: str
    TEI_URL: str
    TEI_PORT: int | None = None
    LLM_PROVIDER: Literal["vllm", "openrouter"]
    OPENROUTER_URL: str
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str


settings = Settings()
