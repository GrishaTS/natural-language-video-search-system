import json

from loguru import logger
from src.infra.ai.client import get_ai_client
from src.infra.ai.llm.schemas import ChatCompletionRequest, ChatCompletionResponse


class AILLMAPI:
    """Client for the AI service chat-completion endpoint."""

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        request_id: str | None = None,
    ) -> ChatCompletionResponse:
        """Send a chat completion request to the AI service.

        Args:
            request: Chat completion request with messages, model, and generation parameters.
            request_id: Optional correlation ID forwarded as ``X-Request-ID``.

        Returns:
            Parsed ChatCompletionResponse.

        Raises:
            httpx.HTTPStatusError: If the AI service returns an error status.
        """

        body = request.model_dump(exclude_none=True)

        if request_id:
            body["request_id"] = request_id

        headers = {"X-Request-ID": request_id} if request_id else None
        client = get_ai_client()
        response = await client.post("/chat/completions", json=body, headers=headers)

        if response.is_error:
            try:
                payload_size = len(json.dumps(body, ensure_ascii=False))
                logger.error(
                    f"AI chat_completion failed: status={response.status_code}, "
                    f"payload_size={payload_size}, response_len={len(response.text or '')}, "
                    f"body={(response.text or '')[:500]}"
                )

            except Exception:
                logger.exception("Failed to log AI chat_completion error details")

        response.raise_for_status()
        data = response.json()

        try:
            return ChatCompletionResponse.model_validate(data)

        except Exception:
            logger.exception(
                f"AI chat_completion returned invalid payload: {str(data)[:500]}"
            )
            raise
