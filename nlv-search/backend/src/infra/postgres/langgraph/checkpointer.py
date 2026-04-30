from contextlib import asynccontextmanager

import psycopg
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from src.core.config import settings


@asynccontextmanager
async def langgraph_checkpointer():
    """Async context manager that yields a ready AsyncPostgresSaver."""

    async with await psycopg.AsyncConnection.connect(
        settings.POSTGRES_URL_PSYCOPG,
        autocommit=True,
        row_factory=dict_row,
    ) as conn:

        yield AsyncPostgresSaver(conn)


async def setup_langgraph_checkpointer() -> None:
    """Create LangGraph checkpoint tables. Call once at startup."""

    async with await psycopg.AsyncConnection.connect(
        settings.POSTGRES_URL_PSYCOPG,
        autocommit=True,
        row_factory=dict_row,
    ) as conn:

        checkpointer = AsyncPostgresSaver(conn)
        await checkpointer.setup()
