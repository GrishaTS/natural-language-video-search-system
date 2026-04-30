from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Service liveness response."""

    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service semantic version")


class HealthServicesResponse(BaseModel):
    """Aggregated health status for all upstream dependencies."""

    postgres: str = Field(..., description="PostgreSQL connectivity status")
    minio: str = Field(..., description="MinIO connectivity status")
    qdrant: str = Field(..., description="Qdrant connectivity status")
    vms: str = Field(..., description="VMS API connectivity status")
    ai: str = Field(..., description="AI service connectivity status")
    redis: str = Field(..., description="Redis connectivity status")
    tei: str = Field(..., description="TEI connectivity status")
    vllm: str = Field(..., description="vLLM connectivity status")
