from fastapi import APIRouter, Depends, HTTPException, status
from src.api.auth.deps import require_service_token
from src.infra.tei.api import tei_api
from src.infra.tei.schemas import EmbedRequest, EmbedResponse

router = APIRouter(prefix="/embed", tags=["embed"])


@router.post("/text", summary="Generate text embeddings", response_model=EmbedResponse)
async def embed_text(
    payload: EmbedRequest,
    _token: str = Depends(require_service_token),
) -> EmbedResponse:
    """Generate text embeddings by proxying the request to the TEI service."""

    try:
        return await tei_api.embed(payload)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
