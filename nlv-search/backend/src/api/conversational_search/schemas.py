from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateChatRequest(BaseModel):
    """Request body for creating a new chat."""

    title: str | None = None


class StreamMessageRequest(BaseModel):
    """Reference schema for streaming message form fields."""

    content: str = Field(min_length=0, max_length=10_000)


class SubmitResolutionRequest(BaseModel):
    """Request body for resuming a graph after entity resolution."""

    resolution_id: str
    selected_ids: list[str] = Field(min_length=1, max_length=100)


class MessageResponse(BaseModel):
    """A single chat message as returned by the API."""

    id: str
    role: str
    type: str
    content: str
    payload: dict[str, Any] | None
    created_at: datetime
    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    """Chat summary returned by list and create endpoints."""

    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    last_message: "MessageResponse | None" = None
    model_config = {"from_attributes": True}


class ChatDetailResponse(ChatResponse):
    """Full chat with message history."""

    messages: list[MessageResponse]
