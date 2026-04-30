from pydantic import BaseModel


class EmbedRequest(BaseModel):
    """Request body for the /embed/text endpoint."""

    texts: list[str]
    request_id: str | None = None


class EmbedResponse(BaseModel):
    """Response from the /embed/text endpoint."""

    embeddings: list[list[float]]
