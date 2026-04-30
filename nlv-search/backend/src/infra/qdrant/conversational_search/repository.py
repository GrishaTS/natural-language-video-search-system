from qdrant_client import AsyncQdrantClient
from qdrant_client.models import ScoredPoint
from src.infra.qdrant.database import qdrant_client


class ConversationalSearchQdrantRepository:
    """Qdrant search for entity resolution candidates.

    No score threshold is applied; the LLM decides relevance from top-k results.
    """

    def __init__(self) -> None:
        self.client: AsyncQdrantClient = qdrant_client

    async def _search(
        self, collection: str, query_vector: list[float], top_k: int
    ) -> list[ScoredPoint]:
        """Query a Qdrant collection by dense vector and return raw scored points.

        Args:
            collection: Qdrant collection name.
            query_vector: Dense query embedding.
            top_k: Maximum number of results to return.

        Returns:
            List of ScoredPoint objects from Qdrant.
        """

        resp = await self.client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=top_k,
        )
        return resp.points

    async def search_people(
        self, query_vector: list[float], top_k: int = 10
    ) -> list[dict]:
        """Search the ``people`` collection and return normalized hit dicts.

        Args:
            query_vector: Dense query embedding.
            top_k: Maximum results.

        Returns:
            List of dicts with keys: id, value, score, first_name, last_name, middle_name.
        """

        hits = await self._search("people", query_vector, top_k)
        return [
            {
                "id": str(hit.id),
                "value": f"{(hit.payload or {}).get('first_name', '')} {(hit.payload or {}).get('last_name', '')}".strip(),
                "score": hit.score,
                "first_name": (hit.payload or {}).get("first_name"),
                "last_name": (hit.payload or {}).get("last_name"),
                "middle_name": (hit.payload or {}).get("middle_name"),
            }
            for hit in hits
        ]

    async def search_locations(
        self, query_vector: list[float], top_k: int = 10
    ) -> list[dict]:
        """Search the ``locations`` collection and return normalized hit dicts.

        Args:
            query_vector: Dense query embedding.
            top_k: Maximum results.

        Returns:
            List of dicts with keys: id, value, score.
        """

        hits = await self._search("locations", query_vector, top_k)
        return [
            {
                "id": str(hit.id),
                "value": (hit.payload or {}).get("address", ""),
                "score": hit.score,
            }
            for hit in hits
        ]

    async def search_vehicles(
        self, query_vector: list[float], top_k: int = 10
    ) -> list[dict]:
        """Search the ``vehicles`` collection and return normalized hit dicts.

        Args:
            query_vector: Dense query embedding.
            top_k: Maximum results.

        Returns:
            List of dicts with keys: id, value, score.
        """

        hits = await self._search("vehicles", query_vector, top_k)
        return [
            {
                "id": str(hit.id),
                "value": (hit.payload or {}).get("number", ""),
                "score": hit.score,
            }
            for hit in hits
        ]
