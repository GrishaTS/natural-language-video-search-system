from src.infra.tei.client import tei_client
from src.infra.tei.schemas import EmbedRequest, EmbedResponse


class TEIApi:
    """Client for the TEI text embeddings service."""

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Lowercase and strip whitespace from a text string before embedding."""

        return text.lower().strip()

    @staticmethod
    def _extract_embeddings(data) -> list[list[float]]:
        """Parse embeddings from various TEI response formats.

        Handles ``{"embeddings": [[...]]}``, raw lists, and OpenAI-style ``{"data": [{"embedding": [...]}]}`` responses.

        Args:
            data: Raw TEI response as dict or list.

        Returns:
            List of embedding vectors.

        Raises:
            ValueError: If the response format is not recognized.
        """

        if isinstance(data, dict):
            if isinstance(data.get("embeddings"), list):
                return data["embeddings"]

            if isinstance(data.get("data"), list):
                return [
                    item.get("embedding")
                    for item in data["data"]
                    if isinstance(item, dict) and item.get("embedding")
                ]

        if isinstance(data, list):
            return data

        raise ValueError(f"Unexpected TEI response format: {data}")

    async def embed(self, payload: EmbedRequest) -> EmbedResponse:
        """Embed a list of texts using the TEI service.

        Args:
            payload: EmbedRequest with text list and optional request ID.

        Returns:
            EmbedResponse containing embedding vectors.

        Raises:
            httpx.HTTPStatusError: If TEI returns a non-2xx response.
        """

        headers = {"X-Request-ID": payload.request_id} if payload.request_id else {}
        normalized_texts = [self._normalize_text(text) for text in payload.texts]
        response = await tei_client.post(
            "/embed",
            json={"inputs": normalized_texts},
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        embeddings = self._extract_embeddings(data)
        return EmbedResponse(embeddings=embeddings)


tei_api = TEIApi()
