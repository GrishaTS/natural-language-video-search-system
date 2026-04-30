from loguru import logger
from qdrant_client.models import Distance, VectorParams
from src.infra.qdrant.database import qdrant_client

COLLECTIONS = ("people", "locations", "vehicles", "aliases")

VECTOR_SIZE = 768


async def ensure_collections(targets: list[str]) -> None:
    """Create or recreate Qdrant collections for the given target names.

    Recreates any collection whose vector size or distance metric does not match the expected configuration.

    Args:
        targets: Collection names to ensure, for example ``["people", "vehicles"]``.
    """

    collections = await qdrant_client.get_collections()
    existing = {c.name: c for c in collections.collections}

    for name in targets:
        collection_info = existing.get(name)

        if not collection_info:
            await qdrant_client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            continue

        current_size = None
        current_distance = None

        try:
            vectors = collection_info.config.params.vectors

            if hasattr(vectors, "size"):
                current_size = vectors.size
                current_distance = vectors.distance

            elif isinstance(vectors, dict) and vectors:
                first = next(iter(vectors.values()))
                current_size = getattr(first, "size", None)
                current_distance = getattr(first, "distance", None)

        except Exception:
            logger.warning(f"Failed to read vectors config for collection '{name}'")

        if current_size != VECTOR_SIZE or current_distance not in (
            None,
            Distance.COSINE,
        ):

            logger.info(
                f"Recreating Qdrant collection '{name}' "
                f"with size={VECTOR_SIZE} distance={Distance.COSINE}"
            )
            await qdrant_client.delete_collection(name)
            await qdrant_client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )


async def get_empty_collections() -> list[str]:
    """Return names of collections that do not exist or have zero points.

    Returns:
        List of collection names that need to be populated.
    """

    empty: list[str] = []

    for name in COLLECTIONS:
        if not await qdrant_client.collection_exists(name):
            empty.append(name)
            continue

        result = await qdrant_client.count(collection_name=name, exact=True)

        if result.count == 0:
            logger.info(f"Qdrant collection '{name}' is empty")
            empty.append(name)

    return empty


async def log_collection_counts() -> None:
    """Log the current point count for each known Qdrant collection."""

    for name in COLLECTIONS:
        result = await qdrant_client.count(collection_name=name, exact=True)
        count = result.count or 0
        logger.info(f"Qdrant collection '{name}': {count} points")


async def cleanup() -> None:
    """Delete all known Qdrant collections."""

    for name in COLLECTIONS:
        await qdrant_client.delete_collection(name)
