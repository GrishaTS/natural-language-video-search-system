import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from src.core import security
from src.core.config import settings
from src.infra.minio.database import get_s3_client
from src.infra.postgres.database import get_session
from src.infra.redis.auth_blacklist import is_token_blacklisted
from src.infra.vms.client import get_vms_client
from src.services.auth.service import AuthService

router = APIRouter(prefix="/api/v1/media", tags=["media"])


@router.get("/snapshot/{path:path}")
async def proxy_vms_snapshot(
    path: str,
    request: Request,
    token: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Proxy VMS snapshot images. Accepts JWT via Authorization header or ?token= query param.

    The frontend's buildImageUrl() prepends API_BASE_URL to the stored relative VMS snapshot
    path and appends ?token=JWT — this endpoint authenticates the user then fetches the image
    from VMS using its own auth token.
    """

    raw_token = token

    if not raw_token:
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            raw_token = auth_header[7:]

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        jwt_payload = security.decode_access_token(raw_token)

    except security.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    if await is_token_blacklisted(raw_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked"
        )

    if not jwt_payload.sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    auth_service = AuthService(session)
    user = await auth_service.get_user_by_id(str(jwt_payload.sub))

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    vms_client = get_vms_client()
    vms_token = await vms_client._get_token()

    query_params = {k: v for k, v in request.query_params.items() if k != "token"}
    vms_url = f"{vms_client.api_url}/api/v1/media/snapshot/{path}"

    async def stream_image():
        """Stream proxied VMS image chunks to the client."""

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            async with client.stream(
                "GET",
                vms_url,
                params=query_params,
                headers={"Authorization": f"Bearer {vms_token}"},
            ) as resp:

                if resp.status_code != 200:
                    return

                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    yield chunk

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
        head_resp = await client.head(
            vms_url,
            params=query_params,
            headers={"Authorization": f"Bearer {vms_token}"},
        )

    content_type = head_resp.headers.get("content-type", "image/jpeg")
    return StreamingResponse(stream_image(), media_type=content_type)


async def _authenticate_token(
    raw_token: str | None,
    session: AsyncSession,
) -> None:
    """Shared auth helper for media proxy endpoints."""

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        jwt_payload = security.decode_access_token(raw_token)

    except security.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    if await is_token_blacklisted(raw_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked"
        )

    if not jwt_payload.sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    auth_service = AuthService(session)
    user = await auth_service.get_user_by_id(str(jwt_payload.sub))

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


@router.get("/chat-image/{key:path}")
async def proxy_chat_image(
    key: str,
    request: Request,
    token: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Proxy chat images stored in MinIO. Accepts JWT via Authorization header or ?token= query param."""

    raw_token = token or ""

    if not raw_token:
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            raw_token = auth_header[7:]

    await _authenticate_token(raw_token, session)

    async with get_s3_client() as s3:
        try:
            obj = await s3.get_object(Bucket=settings.MINIO_BUCKET, Key=key)
            content_type = obj["ContentType"] or "image/jpeg"
            image_bytes = await obj["Body"].read()

        except HTTPException:
            raise

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
            )

    return Response(content=image_bytes, media_type=content_type)
