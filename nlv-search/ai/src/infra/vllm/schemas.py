from typing import Literal

from pydantic import BaseModel


class ResponseMessage(BaseModel):
    """A single message returned in a chat completion response."""

    role: Literal["assistant", "tool", "system", "user"]
    content: str | None = None


class Choice(BaseModel):
    """A single completion choice from the LLM."""

    index: int
    message: ResponseMessage
    finish_reason: Literal["stop", "length", "tool_calls", "content_filter"] | None = (
        None
    )


class Usage(BaseModel):
    """Token usage statistics."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Full OpenAI-compatible chat completion response."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage | None = None
