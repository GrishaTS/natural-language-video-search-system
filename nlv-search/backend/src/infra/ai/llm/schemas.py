from typing import Literal, Union

from pydantic import BaseModel


class RequestMessage(BaseModel):
    """A single message in a chat completion conversation."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_call_id: str | None = None


class ToolFunction(BaseModel):
    """Function metadata for an OpenAI-compatible tool definition."""

    name: str
    description: str | None = None
    parameters: dict[str, object] | None = None


class Tool(BaseModel):
    """OpenAI-compatible function tool definition."""

    type: Literal["function"] = "function"
    function: ToolFunction


class ToolChoiceFunction(BaseModel):
    """Function name selected for explicit tool choice."""

    name: str


class ToolChoice(BaseModel):
    """Explicit function tool choice request."""

    type: Literal["function"]
    function: ToolChoiceFunction


class ChatCompletionRequest(BaseModel):
    """Request body for the OpenAI-compatible chat completions endpoint."""

    model: str
    messages: list[RequestMessage]
    temperature: float | None = 0.7
    top_p: float | None = 1.0
    max_tokens: int | None = None
    stream: bool | None = True
    tools: list[Tool] | None = None
    tool_choice: Union[Literal["auto", "none"], ToolChoice] | None = "auto"


class ResponseMessage(BaseModel):
    """A single message returned in a chat completion response."""

    role: Literal["assistant", "tool", "system", "user"]
    content: str | None = None


class Choice(BaseModel):
    """A single completion choice returned by the LLM."""

    index: int
    message: ResponseMessage
    finish_reason: Literal["stop", "length", "tool_calls", "content_filter"] | None = (
        None
    )


class Usage(BaseModel):
    """Token usage statistics for a chat completion response."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Full response from the chat completions endpoint."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage | None = None
