import json

from loguru import logger
from src.infra.ai.client import get_ai_client
from src.infra.ai.embed.schemas import EmbedRequest, EmbedResponse


class AIEmbedAPI:
    """Client for the AI service text-embedding endpoint."""

    async def embed(
        self,
        request: EmbedRequest,
        request_id: str | None = None,
    ) -> EmbedResponse:
        """Request text embeddings from the AI service.

        Args:
            request: Embed request containing a list of texts.
            request_id: Optional correlation ID forwarded as ``X-Request-ID``.

        Returns:
            EmbedResponse with a list of embedding vectors.

        Raises:
            httpx.HTTPStatusError: If the AI service returns an error status.
        """

        body = request.model_dump(exclude_none=True)

        if request_id:
            body["request_id"] = request_id

        headers = {"X-Request-ID": request_id} if request_id else None
        client = get_ai_client()
        response = await client.post("/embed/text", json=body, headers=headers)

        if response.is_error:
            try:
                payload_size = len(json.dumps(body, ensure_ascii=False))
                logger.error(
                    f"AI embed failed: status={response.status_code}, "
                    f"payload_size={payload_size}, response_len={len(response.text or '')}, "
                    f"body={(response.text or '')[:500]}"
                )

            except Exception:
                logger.exception("Failed to log AI embed error details")

        response.raise_for_status()
        data = response.json()

        try:
            payload = EmbedResponse.model_validate(data)

        except Exception:
            logger.exception(f"AI embed returned invalid payload: {str(data)[:500]}")
            raise

        if not payload.embeddings or len(payload.embeddings[0]) == 0:
            logger.warning(
                f"AI embed returned empty embeddings for request_id={request_id}"
            )

        return payload
