from contextlib import asynccontextmanager

from fastapi import FastAPI
from httpx import ConnectError
from loguru import logger
from src.api.router import api_router
from src.core.config import settings
from src.core.logger import setup_logger
from src.infra.openrouter.client import openrouter_client
from src.infra.tei.client import tei_client
from src.infra.vllm.client import vllm_client

setup_logger(settings.AI_LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: probe upstream dependencies on startup, close clients on shutdown."""

    logger.info("Start AI service")
    llm_client = (
        openrouter_client if settings.LLM_PROVIDER == "openrouter" else vllm_client
    )
    llm_name = settings.LLM_PROVIDER

    try:
        await _check_dependency("tei", tei_client, required=False)
        await _check_dependency(llm_name, llm_client, required=False, path="/models")

    except Exception:
        logger.exception("Dependency health check failed during startup")
        raise

    try:
        yield

    finally:
        await _close_client("tei", tei_client)
        await _close_client(llm_name, llm_client)
        logger.info("Stop AI service")


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

app.include_router(api_router)


async def _check_dependency(
    name: str, client, required: bool = True, path: str = "/health"
) -> None:
    """Probe a dependency health endpoint and log the result.

    Args:
        name: Dependency name used in log messages.
        client: httpx AsyncClient configured for the dependency.
        required: If True, re-raises on failure and halts startup.
        path: Health check path to GET.
    """

    try:
        response = await client.get(path)
        response.raise_for_status()
        logger.info(f"{name} dependency is healthy")

    except ConnectError as exc:
        if required:
            raise

        logger.warning(f"{name} dependency is unavailable: {exc}")

    except Exception:
        if required:
            raise

        logger.warning(f"{name} dependency health check failed (non-fatal)")


async def _close_client(name: str, client) -> None:
    """Close an httpx client if it has an aclose method, logging failures."""

    close = getattr(client, "aclose", None)

    try:
        if callable(close):
            await close()

    except Exception:
        logger.warning(f"Failed to close {name} client cleanly")
