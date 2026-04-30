from fastapi import APIRouter
from loguru import logger
from sqlalchemy import text
from src.api.health.schemas import HealthResponse, HealthServicesResponse
from src.core.config import settings
from src.infra.ai import AIHealthAPI
from src.infra.minio import get_s3_client
from src.infra.postgres.database import postgres_client
from src.infra.qdrant.database import qdrant_client
from src.infra.redis.database import redis_client
from src.infra.vms import VmsAPI

router = APIRouter(prefix="/health", tags=["health"])

ai_health_api = AIHealthAPI()

vms_api = VmsAPI()


@router.get("", summary="Health check", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return the service liveness status."""

    return HealthResponse(
        status="ok",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
    )


@router.get(
    "/services",
    summary="Health check for external services",
    response_model=HealthServicesResponse,
)
async def health_services() -> HealthServicesResponse:
    """Return health status for all upstream dependencies."""

    statuses: dict[str, str] = {}

    try:
        async with postgres_client() as session:
            await session.execute(text("SELECT 1"))

        statuses["postgres"] = "ok"

    except Exception as exc:
        logger.exception("Postgres health check failed")
        statuses["postgres"] = f"error: {exc}"

    try:
        async with get_s3_client() as s3:
            await s3.list_buckets()

        statuses["minio"] = "ok"

    except Exception as exc:
        logger.exception("MinIO health check failed")
        statuses["minio"] = f"error: {exc}"

    try:
        await qdrant_client.get_collections()
        statuses["qdrant"] = "ok"

    except Exception as exc:
        logger.exception("Qdrant health check failed")
        statuses["qdrant"] = f"error: {exc}"

    try:
        await vms_api.health()
        statuses["vms"] = "ok"

    except Exception as exc:
        logger.exception("VMS health check failed")
        statuses["vms"] = f"error: {exc}"

    try:
        data = await ai_health_api.health()
        statuses["ai"] = data.status

    except Exception as exc:
        logger.exception("AI service health check failed")
        statuses["ai"] = f"error: {exc}"

    try:
        ai_services = await ai_health_api.health_services()
        statuses["tei"] = ai_services.tei
        statuses["vllm"] = ai_services.vllm

    except Exception as exc:
        logger.exception("AI service health/services check failed")
        statuses["tei"] = f"error: {exc}"
        statuses["vllm"] = f"error: {exc}"

    try:
        await redis_client.ping()
        statuses["redis"] = "ok"

    except Exception as exc:
        logger.exception("Redis health check failed")
        statuses["redis"] = f"error: {exc}"

    failed = {name: value for name, value in statuses.items() if value != "ok"}

    if failed:
        logger.warning(f"Health check detected issues: {failed}")

    return HealthServicesResponse(**statuses)
