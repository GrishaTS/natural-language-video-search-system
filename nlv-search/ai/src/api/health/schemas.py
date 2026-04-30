from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """AI service liveness response."""

    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service semantic version")


class HealthServicesResponse(BaseModel):
    """Aggregated health status for TEI and the active LLM provider."""

    tei: str = Field(..., description="TEI connectivity status")
    vllm: str | None = Field(None, description="vLLM connectivity status")
    openrouter: str | None = Field(None, description="OpenRouter connectivity status")
