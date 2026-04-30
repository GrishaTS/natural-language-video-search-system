from fastapi import APIRouter
from src.api.health.schemas import HealthResponse, HealthServicesResponse
from src.core.config import settings
from src.infra.openrouter.client import openrouter_client
from src.infra.tei.client import tei_client
from src.infra.vllm.client import vllm_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Health check", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return AI service liveness status."""

    return HealthResponse(
        status="ok",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
    )


@router.get(
    "/services",
    summary="Health check for TEI and LLM provider",
    response_model=HealthServicesResponse,
)
async def health_services() -> HealthServicesResponse:
    """Return health status of all AI service upstream dependencies."""

    statuses: dict[str, str] = {}

    try:
        response = await tei_client.get("/health")
        response.raise_for_status()
        statuses["tei"] = "ok"

    except Exception as exc:
        statuses["tei"] = f"error: {exc}"

    llm_client = (
        openrouter_client if settings.LLM_PROVIDER == "openrouter" else vllm_client
    )
    llm_key = settings.LLM_PROVIDER

    try:
        response = await llm_client.get("/models")
        response.raise_for_status()
        statuses[llm_key] = "ok"

    except Exception as exc:
        statuses[llm_key] = f"error: {exc}"

    return HealthServicesResponse(**statuses)
