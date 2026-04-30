from contextlib import asynccontextmanager
from typing import AsyncIterator

import aioboto3
from loguru import logger
from src.core.config import settings
from types_aiobotocore_s3 import S3Client

_session = aioboto3.Session()


@asynccontextmanager
async def get_s3_client() -> AsyncIterator[S3Client]:
    """Async context manager that yields a configured aioboto3 S3 client."""

    async with _session.client(
        "s3",
        endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ROOT_USER,
        aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
    ) as client:

        yield client


async def ensure_minio_bucket() -> None:
    """Create the configured MinIO bucket if it does not already exist."""

    async with get_s3_client() as s3:
        try:
            await s3.head_bucket(Bucket=settings.MINIO_BUCKET)
            logger.info(f"MinIO bucket '{settings.MINIO_BUCKET}' already exists")

        except Exception:
            await s3.create_bucket(Bucket=settings.MINIO_BUCKET)
            logger.info(f"MinIO bucket '{settings.MINIO_BUCKET}' created")
