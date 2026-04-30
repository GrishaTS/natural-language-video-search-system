from pydantic import BaseModel, Field


class AIHealthResponse(BaseModel):
    """Overall health status of the AI service."""

    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service semantic version")


class AIHealthServicesResponse(BaseModel):
    """Per-service health status for AI service dependencies."""

    tei: str = Field(..., description="TEI connectivity status")
    vllm: str = Field(..., description="vLLM connectivity status")
