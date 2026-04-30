import httpx
from loguru import logger
from src.infra.vllm.client import vllm_client
from src.infra.vllm.schemas import ChatCompletionResponse


class VLLMApi:
    """Client for the vLLM OpenAI-compatible inference server."""

    async def _raise_vllm_error(self, response: httpx.Response) -> None:
        """Read and log the error body, then raise for non-2xx responses."""

        if not response.is_error:
            return

        body_preview = (await response.aread()).decode(errors="replace")[:500]
        logger.error(
            f"vLLM chat_completion failed: status={response.status_code}, "
            f"body={body_preview}"
        )
        response.raise_for_status()

    async def chat_completion(
        self,
        body: dict,
        request_id: str | None = None,
    ) -> ChatCompletionResponse:
        """Send a non-streaming chat completion request to vLLM.

        Args:
            body: OpenAI-compatible request body dict.
            request_id: Optional correlation ID sent as ``X-Request-ID``.

        Returns:
            Parsed ChatCompletionResponse.

        Raises:
            httpx.HTTPStatusError: If vLLM returns a non-2xx response.
        """

        headers = {"X-Request-ID": request_id} if request_id else {}
        response = await vllm_client.post(
            "/chat/completions",
            json=body,
            headers=headers or None,
        )
        await self._raise_vllm_error(response)
        return ChatCompletionResponse.model_validate(response.json())

    async def stream_chat_completion(
        self,
        body: dict,
        request_id: str | None = None,
    ) -> httpx.Response:
        """Send a streaming chat completion request to vLLM.

        Args:
            body: OpenAI-compatible request body dict with streaming enabled.
            request_id: Optional correlation ID sent as ``X-Request-ID``.

        Returns:
            Open httpx.Response in streaming mode. Caller must close it.

        Raises:
            httpx.HTTPStatusError: If vLLM returns a non-2xx response.
        """

        headers = {"X-Request-ID": request_id} if request_id else {}
        request = vllm_client.build_request(
            "POST",
            "/chat/completions",
            json=body,
            headers=headers or None,
        )
        response = await vllm_client.send(request, stream=True)

        try:
            await self._raise_vllm_error(response)

        except Exception:
            await response.aclose()
            raise

        return response


vllm_api = VLLMApi()
