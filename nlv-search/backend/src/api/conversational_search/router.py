import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from loguru import logger
from src.api.auth.deps import get_current_user
from src.api.conversational_search.schemas import (
    ChatDetailResponse,
    ChatResponse,
    CreateChatRequest,
    MessageResponse,
    SubmitResolutionRequest,
)
from src.infra.minio.conversational_search import ConversationalSearchMinioRepository
from src.infra.postgres.auth import User
from src.infra.postgres.conversational_search import ChatRepository
from src.infra.postgres.database import postgres_client
from src.services.conversational_search.service import ConversationalSearchService

router = APIRouter(prefix="/chats", tags=["conversational-search"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    body: CreateChatRequest,
    user: User = Depends(get_current_user),
):
    """Create a new chat session for the authenticated user."""

    async with postgres_client() as session:
        repo = ChatRepository(session)
        chat = await repo.create_chat(user_id=str(user.id), title=body.title)
        await session.commit()
        await session.refresh(chat)

    return ChatResponse.model_validate(chat)


@router.get("", response_model=list[ChatResponse])
async def list_chats(
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
):
    """Return a paginated list of the user chats with their last message."""

    async with postgres_client() as session:
        repo = ChatRepository(session)
        rows = await repo.list_user_chats(
            user_id=str(user.id), limit=limit, offset=offset
        )

    result = []

    for chat, last_msg in rows:
        data = ChatResponse.model_validate(chat)
        data.last_message = (
            MessageResponse.model_validate(last_msg) if last_msg else None
        )
        result.append(data)

    return result


@router.get("/{chat_id}", response_model=ChatDetailResponse)
async def get_chat(
    chat_id: str,
    user: User = Depends(get_current_user),
):
    """Return a single chat with all its messages and proxied image URLs."""

    async with postgres_client() as session:
        repo = ChatRepository(session)
        chat = await repo.get_chat_with_messages(chat_id=chat_id, user_id=str(user.id))

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
        )

    messages: list[MessageResponse] = []

    for m in chat.messages:
        msg = MessageResponse.model_validate(m)

        if msg.payload and msg.payload.get("image_key"):
            msg.payload["image_url"] = (
                f"/api/v1/media/chat-image/{msg.payload['image_key']}"
            )

        messages.append(msg)

    return ChatDetailResponse(
        id=chat.id,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        messages=messages,
    )


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: str,
    user: User = Depends(get_current_user),
):
    """Delete a chat and cascade-delete its MinIO images."""

    async with postgres_client() as session:
        repo = ChatRepository(session)

        image_keys = await repo.get_image_keys(chat_id)
        deleted = await repo.delete_chat(chat_id=chat_id, user_id=str(user.id))
        await session.commit()

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
        )

    if image_keys:
        minio_repo = ConversationalSearchMinioRepository()
        await minio_repo.delete_images(image_keys)


@router.post("/{chat_id}/messages/stream")
async def stream_message(
    chat_id: str,
    content: str = Form("", max_length=10_000),
    image: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
):
    """Start an SSE stream for a new user message containing text and/or photo."""

    has_text = bool(content and content.strip())
    has_image = image is not None and image.size and image.size > 0
    logger.info(
        f"stream_message: chat_id={chat_id}, user_id={user.id}, has_text={has_text}, has_image={has_image}"
    )

    if not has_text and not has_image:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either content or image must be provided",
        )

    async with postgres_client() as session:
        repo = ChatRepository(session)
        chat = await repo.get_chat(chat_id=chat_id)

    if not chat or chat.user_id != str(user.id):
        logger.warning(
            f"stream_message: chat_id={chat_id} not found or forbidden for user_id={user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
        )

    image_bytes: bytes | None = None
    image_content_type: str = "image/jpeg"

    if has_image:
        image_bytes = await image.read()
        image_content_type = image.content_type or "image/jpeg"

    svc = ConversationalSearchService()

    async def event_generator():
        """Yield server-sent event frames for a new message stream."""

        try:
            async for event in svc.stream(
                chat_id,
                str(user.id),
                content,
                image_bytes=image_bytes,
                image_content_type=image_content_type,
            ):

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as exc:
            import traceback as _tb

            logger.error(
                f"stream_message: unhandled error chat_id={chat_id}: {type(exc).__name__}: {exc}\n{_tb.format_exc()}"
            )
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{chat_id}/resolution")
async def submit_resolution(
    chat_id: str,
    body: SubmitResolutionRequest,
    user: User = Depends(get_current_user),
):
    """Resume a paused graph stream after the user resolves an entity selection."""

    async with postgres_client() as session:
        repo = ChatRepository(session)
        chat = await repo.get_chat(chat_id=chat_id)

    if not chat or chat.user_id != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
        )

    svc = ConversationalSearchService()

    async def event_generator():
        """Yield server-sent event frames while resuming a resolved graph interrupt."""

        try:
            async for event in svc.resume(
                chat_id, str(user.id), body.resolution_id, body.selected_ids
            ):

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as exc:
            import traceback as _tb

            logger.error(
                f"submit_resolution: unhandled error chat_id={chat_id}: {type(exc).__name__}: {exc}\n{_tb.format_exc()}"
            )
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
