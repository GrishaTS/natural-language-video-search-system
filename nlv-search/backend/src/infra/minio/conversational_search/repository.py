from __future__ import annotations

import asyncio
from urllib.parse import urlparse
from uuid import uuid4

from src.core.config import settings
from src.infra.minio.database import get_s3_client


class ConversationalSearchMinioRepository:
    """MinIO repository for chat image storage."""

    def __init__(self, bucket: str | None = None) -> None:
        """Initialize with an optional bucket name; defaults to ``settings.MINIO_BUCKET``."""

        self.bucket = bucket or settings.MINIO_BUCKET

    async def upload_chat_image(
        self,
        chat_id: str,
        image_bytes: bytes,
        content_type: str = "image/jpeg",
    ) -> str:
        """Upload an image to MinIO and return its object key.

        Args:
            chat_id: Chat ID used to namespace the key.
            image_bytes: Raw image bytes.
            content_type: MIME type of the image.

        Returns:
            MinIO object key, not a presigned URL.
        """

        key = f"chat-images/{chat_id}/{uuid4()}"

        async with get_s3_client() as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=image_bytes,
                ContentType=content_type,
            )

        return key

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned GET URL for an object.

        Args:
            key: MinIO object key.
            expires_in: URL validity in seconds.

        Returns:
            Presigned URL string.
        """

        async with get_s3_client() as s3:
            return await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )

    async def delete_images(self, keys: list[str]) -> None:
        """Delete multiple objects from MinIO concurrently.

        Args:
            keys: List of MinIO object keys to delete.
        """

        if not keys:
            return

        async with get_s3_client() as s3:
            await asyncio.gather(
                *[s3.delete_object(Bucket=self.bucket, Key=k) for k in keys]
            )
