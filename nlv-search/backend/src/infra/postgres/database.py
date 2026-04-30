import asyncio
from typing import AsyncIterator, Tuple

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from src.core.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""


_engine: AsyncEngine | None = None

_session_factory: async_sessionmaker[AsyncSession] | None = None

LEGACY_CONVERSATIONAL_SEARCH_TABLES = (
    "pipeline_metrics",
    "resolution_options",
    "event_cache",
    "search_results",
    "search_requests",
    "entity_attributes",
)


def _ensure_engine() -> Tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Lazily create the engine/sessionmaker to avoid DB work at import time."""

    global _engine, _session_factory

    if _engine is None or _session_factory is None:
        _engine = create_async_engine(settings.POSTGRES_URL, pool_pre_ping=True)
        _session_factory = async_sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.debug(f"Postgres engine created for {settings.POSTGRES_URL}")

    return _engine, _session_factory


def postgres_client() -> AsyncSession:
    """Return a new AsyncSession (keeps compatibility with `async with postgres_client()`)."""

    _, factory = _ensure_engine()
    return factory()


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a database session per request."""

    async with postgres_client() as session:
        yield session


async def init_db(retries: int = 5, delay_seconds: float = 1.0) -> None:
    """Create tables if they don't exist, with simple retries for startup races."""

    from src.infra.postgres.auth import models
    from src.infra.postgres.conversational_search import (
        models as cs_models,
    )

    engine, _ = _ensure_engine()

    for attempt in range(1, retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                await conn.run_sync(Base.metadata.create_all)

                for table_name in LEGACY_CONVERSATIONAL_SEARCH_TABLES:
                    await conn.execute(
                        text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
                    )

            logger.info("Postgres schema initialized")
            return

        except Exception as exc:
            logger.exception(f"Postgres init attempt {attempt}/{retries} failed")

            if attempt == retries:
                raise

            await asyncio.sleep(delay_seconds * attempt)


async def seed_users() -> None:
    """Create default users if they don't exist."""

    from src.core import security
    from src.infra.postgres.auth import User, UserRepository

    default_users = [
        {"username": "griga", "email": "griga@example.com"},
        {"username": "vadim", "email": "vadim@example.com"},
        {"username": "igor", "email": "igor@example.com"},
        {"username": "german", "email": "german@example.com"},
        {"username": "nik", "email": "nik@example.com"},
    ]
    password_hash = security.get_password_hash(settings.DEFAULT_USER_PASSWORD)

    if settings.NLV_BOT_USERNAME and settings.NLV_BOT_PASSWORD:
        default_users.append(
            {
                "username": settings.NLV_BOT_USERNAME,
                "email": f"{settings.NLV_BOT_USERNAME}@bot.example.com",
                "_password_hash": security.get_password_hash(settings.NLV_BOT_PASSWORD),
            }
        )

    async with postgres_client() as session:
        repo = UserRepository(session)

        for user_data in default_users:
            existing = await repo.get_by_username(user_data["username"])

            if existing:
                continue

            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=user_data.get("_password_hash", password_hash),
            )
            session.add(user)
            logger.info(f"Created user '{user_data['username']}'")

        await session.commit()

    logger.info("User seeding completed")


async def close_postgres_client() -> None:
    """Dispose the SQLAlchemy engine and release all connections."""

    global _engine, _session_factory
    engine = _engine

    if engine is None:
        return

    await engine.dispose()
    logger.info("Postgres engine disposed")
    _engine = None
    _session_factory = None
