from pydantic import BaseModel


class EmbedRequest(BaseModel):
    """Request body for the /embed endpoint."""

    texts: list[str]
    request_id: str | None = None


class EmbedResponse(BaseModel):
    """Response from the /embed endpoint containing embedding vectors."""

    embeddings: list[list[float]]
