from src.infra.ai import AIEmbedAPI
from src.infra.vms import VmsAPI
from src.services.entities_populator import collections, qdrant_upsert


class EntitiesPopulatorService:
    """Populate entity indexes in Qdrant from VmsAPI."""

    def __init__(self) -> None:
        """Initialize VMS API client and AI embed client."""

        self.vms_api = VmsAPI()
        self.ai = AIEmbedAPI()

    async def populate(self, targets: list[str]) -> None:
        """Fetch entities from VMS and upsert them into Qdrant.

        Args:
            targets: Collection names to populate. Include ``"aliases"`` to also generate name alias variants.
        """

        make_aliases = "aliases" in targets
        await collections.ensure_collections(targets)
        aliases_inserted = 0

        if "people" in targets or make_aliases:
            people = await self.vms_api.get_all_people()
            aliases_inserted += await qdrant_upsert.upsert_people(
                self.ai,
                people,
                write_collection="people" in targets,
                make_aliases=make_aliases,
            )

        if "vehicles" in targets:
            vehicles = await self.vms_api.get_all_vehicles()
            await qdrant_upsert.upsert_vehicles(self.ai, vehicles)

        if "locations" in targets or make_aliases:
            locations = await self.vms_api.get_all_locations()
            aliases_inserted += await qdrant_upsert.upsert_locations(
                self.ai,
                locations,
                write_collection="locations" in targets,
                make_aliases=make_aliases,
            )

        if make_aliases:
            from loguru import logger

            logger.info(f"Inserted aliases: {aliases_inserted}")

    async def cleanup(self) -> None:
        """Delete all Qdrant entity collections."""

        await collections.cleanup()

    async def get_empty_collections(self) -> list[str]:
        """Return names of Qdrant collections that are missing or empty.

        Returns:
            List of collection names that need population.
        """

        return await collections.get_empty_collections()

    async def log_collection_counts(self) -> None:
        """Log the current point count for each Qdrant collection."""

        await collections.log_collection_counts()
