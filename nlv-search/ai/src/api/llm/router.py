from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from src.api.auth.deps import require_service_token
from src.core.config import settings
from src.infra.openrouter.api import openrouter_api
from src.infra.vllm.api import vllm_api
from starlette.background import BackgroundTask

router = APIRouter(tags=["llm"])


def _get_llm_api():
    """Return the active LLM API client and model name based on ``LLM_PROVIDER``."""

    if settings.LLM_PROVIDER == "openrouter":
        return openrouter_api, settings.OPENROUTER_MODEL

    return vllm_api, settings.VLLM_MODEL


async def _chat_completions(request: Request) -> StreamingResponse:
    """Route a chat completion request to the configured LLM provider.

    Handles both streaming and non-streaming modes. Injects the configured model name and forwards the request to vLLM or OpenRouter.

    Args:
        request: Raw FastAPI request with a JSON body.

    Returns:
        StreamingResponse for streaming requests, or a parsed response object.

    Raises:
        HTTPException: If the upstream LLM returns an error.
    """

    body: dict = await request.json()
    request_id: str | None = body.pop("request_id", None)
    llm_api, model = _get_llm_api()
    body["model"] = model

    try:
        if body.get("stream", True):
            upstream = await llm_api.stream_chat_completion(body, request_id=request_id)
            headers = {}

            if ct := upstream.headers.get("content-type"):
                headers["content-type"] = ct

            if cc := upstream.headers.get("cache-control"):
                headers["cache-control"] = cc

            return StreamingResponse(
                upstream.aiter_raw(),
                status_code=upstream.status_code,
                headers=headers or None,
                background=BackgroundTask(upstream.aclose),
            )

        return await llm_api.chat_completion(body, request_id=request_id)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc


@router.post(
    "/chat/completions",
    summary="Proxy chat completion to LLM provider",
    response_model=None,
)
async def chat_completions(
    request: Request,
    _token: str = Depends(require_service_token),
):
    """Proxy chat completion to the configured LLM provider."""

    return await _chat_completions(request)


@router.post(
    "/v1/chat/completions",
    summary="OpenAI-compatible chat completion path",
    response_model=None,
)
async def v1_chat_completions(
    request: Request,
    _token: str = Depends(require_service_token),
):
    """OpenAI-compatible alias for the chat completion proxy endpoint."""

    return await _chat_completions(request)
