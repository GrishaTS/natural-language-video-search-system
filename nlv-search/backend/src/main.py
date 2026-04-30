from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from src.api.router import api_router
from src.core.config import settings
from src.core.logger import setup_logger
from src.infra.ai import aclose_ai_client
from src.infra.minio import ensure_minio_bucket
from src.infra.postgres.database import close_postgres_client, init_db, seed_users
from src.infra.postgres.langgraph import setup_langgraph_checkpointer
from src.infra.qdrant.database import close_qdrant_client
from src.infra.redis.database import close_redis_client
from src.infra.vms import aclose_vms_client

setup_logger(settings.BACKEND_LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: initialize all infrastructure on startup, close on shutdown.

    Startup order: Postgres schema, seed users, LangGraph checkpointer, MinIO bucket, and Qdrant entity population. Shutdown closes Postgres, Redis, Qdrant, VMS, and AI clients.
    """

    logger.info(
        f"Starting backend service on {settings.BACKEND_HOST}:{settings.BACKEND_PORT}"
    )

    try:
        try:
            await init_db()

        except Exception:
            logger.exception("Failed to initialize database schema")
            raise

        try:
            await seed_users()

        except Exception:
            logger.exception("Failed to seed users")
            raise

        try:
            await setup_langgraph_checkpointer()
            logger.info("LangGraph checkpointer tables initialized")

        except Exception:
            logger.exception("Failed to initialize LangGraph checkpointer")
            raise

        try:
            await ensure_minio_bucket()

        except Exception:
            logger.exception("Failed to ensure MinIO bucket")
            raise

        try:
            from src.services.entities_populator import EntitiesPopulatorService

            populator = EntitiesPopulatorService()
            empty = await populator.get_empty_collections()

            if empty:
                logger.info(f"Populating empty Qdrant collections: {empty}")
                await populator.populate(targets=empty)
                await populator.log_collection_counts()

        except Exception:
            logger.exception("Failed to populate entity collections")
            raise

        yield

    finally:
        try:
            await close_postgres_client()

        except Exception:
            logger.exception("Failed to close database engine")

        try:
            await close_redis_client()

        except Exception:
            logger.exception("Failed to close Redis client")

        try:
            await close_qdrant_client()

        except Exception:
            logger.exception("Failed to close Qdrant client")

        try:
            await aclose_vms_client()

        except Exception:
            logger.exception("Failed to close VMS client")

        try:
            await aclose_ai_client()

        except Exception:
            logger.exception("Failed to close AI client session")

        logger.info("Backend service shut down")


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

app.include_router(api_router)
