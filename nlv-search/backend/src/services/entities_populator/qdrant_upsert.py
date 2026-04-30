import hashlib

from loguru import logger
from qdrant_client.models import PointStruct
from src.domain.entity_naming import person_alias_variants
from src.infra.ai import AIEmbedAPI, EmbedRequest
from src.infra.qdrant.database import qdrant_client
from src.infra.vms.schemas import LocationInfo, PersonFullName, VehicleInfo


def alias_id(seed: str) -> int:
    """Derive a stable 64-bit integer ID from a seed string via SHA-1.

    Args:
        seed: Arbitrary string used as the hash input.

    Returns:
        Unsigned 64-bit integer suitable as a Qdrant point ID.
    """

    digest = hashlib.sha1(seed.encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _is_russian_address(address: str) -> bool:
    """Return True if address is Russian (not Belarusian or other non-Russian variant).

    Belarusian markers:
    - Cyrillic 'і' (U+0456) — present in Belarusian, absent in Russian
    - Belarusian-specific street/city tokens
    """

    if "\u0456" in address:
        return False

    lower = address.lower()
    belarusian_tokens = ("вуліц", "раён", "мінск", "завулак", "праспект")
    return not any(tok in lower for tok in belarusian_tokens)


async def upsert_people(
    ai: AIEmbedAPI,
    people: list[PersonFullName],
    write_collection: bool = True,
    make_aliases: bool = False,
) -> int:
    """Embed and upsert person records into the ``people`` Qdrant collection.

    Args:
        ai: AI embed API client.
        people: List of PersonFullName dicts from VMS.
        write_collection: If True, upsert into the people collection.
        make_aliases: If True, generate and upsert name alias variants into aliases.

    Returns:
        Total number of alias points inserted.
    """

    batch_size = 20
    alias_total = 0
    people_total = 0

    for i in range(0, len(people), batch_size):
        batch = people[i : i + batch_size]
        with_text = [
            (
                person,
                " ".join(
                    filter(
                        None,
                        [
                            person.get("first_name"),
                            person.get("middle_name"),
                            person.get("last_name"),
                        ],
                    )
                ).strip(),
            )
            for person in batch
        ]
        with_text = [(p, t) for p, t in with_text if t]

        if not with_text:
            continue

        embeddings = await ai.embed(EmbedRequest(texts=[text for _, text in with_text]))
        points: list[PointStruct] = []
        alias_points: list[PointStruct] = []

        for (person, _), emb in zip(with_text, embeddings.embeddings):
            if not emb:
                continue

            payload = {
                "first_name": person.get("first_name"),
                "last_name": person.get("last_name"),
                "middle_name": person.get("middle_name"),
            }
            points.append(PointStruct(id=person["id"], vector=emb, payload=payload))
            people_total += 1

            if make_aliases:
                for alias_text in person_alias_variants(
                    person.get("first_name") or "",
                    person.get("middle_name") or "",
                    person.get("last_name") or "",
                ):

                    alias_points.append(
                        PointStruct(
                            id=alias_id(f"person-{person['id']}-{alias_text}"),
                            vector=emb,
                            payload={
                                "alias": alias_text,
                                "type": "person",
                                "first_name": payload.get("first_name", ""),
                                "last_name": payload.get("last_name", ""),
                                "middle_name": payload.get("middle_name", ""),
                                "ref_id": person["id"],
                                "person_id": person["id"],
                            },
                        )
                    )

        if write_collection and points:
            await qdrant_client.upsert(
                collection_name="people", wait=True, points=points
            )

        if make_aliases and alias_points:
            await qdrant_client.upsert(
                collection_name="aliases", wait=True, points=alias_points
            )
            alias_total += len(alias_points)

    if write_collection and people_total:
        logger.info(f"Inserted people: {people_total}")

    return alias_total


async def upsert_locations(
    ai: AIEmbedAPI,
    locations: list[LocationInfo],
    write_collection: bool = True,
    make_aliases: bool = False,
) -> int:
    """Embed and upsert location records into the ``locations`` Qdrant collection.

    Filters out non-Russian addresses before embedding.

    Args:
        ai: AI embed API client.
        locations: List of LocationInfo dicts from VMS.
        write_collection: If True, upsert into the locations collection.
        make_aliases: Reserved for future alias generation.

    Returns:
        Always returns 0 because alias generation is not implemented for locations.
    """

    unique_addresses: dict[str, None] = {}

    for loc in locations:
        address = (loc.get("address") or "").strip()

        if address:
            unique_addresses[address] = None

    locations_list = list(unique_addresses.keys())
    filtered_list = [addr for addr in locations_list if _is_russian_address(addr)]
    logger.info(
        f"Upserting locations: total={len(locations)} unique_addresses={len(locations_list)} "
        f"after_language_filter={len(filtered_list)}"
    )
    locations_list = filtered_list
    batch_size = 25
    locations_total = 0

    for i in range(0, len(locations_list), batch_size):
        batch = locations_list[i : i + batch_size]

        if not batch:
            continue

        try:
            embeddings = await ai.embed(EmbedRequest(texts=batch))

        except Exception:
            logger.exception("Failed to embed locations batch; skipping")
            continue

        points: list[PointStruct] = []

        for text, emb in zip(batch, embeddings.embeddings):
            if not emb:
                continue

            point_id = alias_id(f"loc-{text}")
            points.append(
                PointStruct(id=point_id, vector=emb, payload={"address": text})
            )
            locations_total += 1

        if write_collection and points:
            await qdrant_client.upsert(
                collection_name="locations", wait=True, points=points
            )

    if write_collection and locations_total:
        logger.info(f"Inserted locations: {locations_total}")

    return 0


async def upsert_vehicles(ai: AIEmbedAPI, vehicles: list[VehicleInfo]) -> None:
    """Embed and upsert vehicle records into the ``vehicles`` Qdrant collection.

    Args:
        ai: AI embed API client.
        vehicles: List of VehicleInfo dicts from VMS.
    """

    batch_size = 25
    total_inserted = 0

    for i in range(0, len(vehicles), batch_size):
        batch = vehicles[i : i + batch_size]
        with_text = [(v, (v.get("number") or "").strip()) for v in batch]
        with_text = [(v, t) for v, t in with_text if t]

        if not with_text:
            continue

        embeddings = await ai.embed(EmbedRequest(texts=[text for _, text in with_text]))
        points: list[PointStruct] = []

        for (vehicle, number), emb in zip(with_text, embeddings.embeddings):
            if not emb:
                continue

            points.append(
                PointStruct(id=vehicle["id"], vector=emb, payload={"number": number})
            )
            total_inserted += 1

        if not points:
            continue

        await qdrant_client.upsert(collection_name="vehicles", wait=True, points=points)

    if total_inserted:
        logger.info(f"Inserted vehicles: {total_inserted}")
