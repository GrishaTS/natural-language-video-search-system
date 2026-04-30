from typing import Any

from loguru import logger
from src.infra.vms.client import VmsClient, get_vms_client
from src.infra.vms.schemas import (
    EventFilter,
    LocationInfo,
    PersonFullName,
    VehicleInfo,
)


class VmsAPI:
    """High-level VMS API facade built on top of VmsClient.

    Groups domain-specific operations: event search, face recognition, entity listing for people, vehicles, and locations, and media proxying.
    """

    def __init__(self, client: VmsClient | None = None) -> None:
        """Initialize with an optional VmsClient; defaults to the shared singleton."""

        self.client = client or get_vms_client()

    async def health(self):
        """Return a health indicator by performing a lightweight VMS API call."""

        return await self.get_all_vehicles()

    async def search_events(self, event_filter: EventFilter) -> Any:
        """Search video events using the given filter.

        Args:
            event_filter: Structured filter with domain, time range, entities, and locations.

        Returns:
            Raw VMS response as returned by the event search endpoint.
        """

        json_data = event_filter.model_dump(mode="json")
        logger.info(f"vms.search_events(event_filter={json_data})")
        response = await self.client.request(
            "POST",
            "/edge-api/api/v1/events/search",
            json_data=json_data,
        )
        return response

    async def get_face_descriptor(self, image_bytes: bytes) -> dict:
        """Extract a face descriptor from an uploaded image.

        Args:
            image_bytes: Raw image data such as JPEG or PNG.

        Returns:
            Dict with ``descriptor`` and ``version`` keys.
        """

        response = await self.client.request_multipart(
            "POST",
            "/api/v1/face-descriptor",
            file_bytes=image_bytes,
            file_field="file",
        )
        descriptor_data = response[0][0]
        return {
            "descriptor": descriptor_data["descriptor"],
            "version": descriptor_data["version"],
        }

    async def search_faces_by_descriptor(
        self,
        descriptor: dict,
        min_similarity: float = 0.7,
        limit: int = 10,
    ) -> list[dict]:
        """Search the face registry by descriptor similarity.

        Args:
            descriptor: Face descriptor dict with ``descriptor`` and ``version`` keys.
            min_similarity: Minimum similarity threshold.
            limit: Maximum number of results.

        Returns:
            List of face match dicts from the VMS face manager.
        """

        payload = {
            "face_match": {
                "descriptors": [
                    {
                        "descriptor": descriptor["descriptor"],
                        "version": descriptor["version"],
                    }
                ],
                "min_similarity": min_similarity,
            },
            "limit": limit,
        }
        return await self.client.request(
            "POST",
            "/face-manager/api/v1/faces/search",
            json_data=payload,
        )

    async def search_people(
        self,
        first_name: str | None = None,
        last_name: str | None = None,
        middle_name: str | None = None,
        limit: int = 10,
    ):
        """Search the face registry by person name fields.

        Args:
            first_name: Optional first name filter.
            last_name: Optional last name filter.
            middle_name: Optional middle name filter.
            limit: Maximum number of results.

        Returns:
            Raw VMS face search response.
        """

        person = {
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name,
        }
        person = {k: v for k, v in person.items() if v}
        return await self.client.request(
            "POST",
            "/face-manager/api/v1/faces/search",
            json_data={"person": person, "limit": limit},
        )

    async def search_vehicles(self, number: str, limit: int = 10):
        """Search the plate registry by vehicle plate number.

        Args:
            number: Plate number string.
            limit: Maximum number of results.

        Returns:
            Raw VMS plate search response.
        """

        plate = {"number": number}
        return await self.client.request(
            "POST",
            "/edge-api/api/v1/plates/search",
            json_data={"plate": plate, "limit": limit},
        )

    async def search_locations(self, address: str, limit: int = 10):
        """Search VMS locations by address text.

        Args:
            address: Address string to search for.
            limit: Maximum number of results.

        Returns:
            Raw VMS location search response.
        """

        return await self.client.request(
            "POST",
            "/edge-api/api/v1/locations/search",
            json_data={"location": {"text": address}, "limit": limit},
        )

    async def search_tags(self, tag_name: str):
        """Search VMS tags by name.

        Args:
            tag_name: Tag name to search for.

        Returns:
            Raw VMS tag search response.
        """

        return await self.client.request(
            "POST",
            "/edge-api/api/v1/tags/search",
            json_data={"tag": {"name": tag_name}},
        )

    async def get_all_people(self) -> list[PersonFullName]:
        """Fetch all persons from the face registry with pagination.

        Returns:
            List of PersonFullName dicts.
        """

        limit = 500
        offset = 0
        result = []
        json_data = {
            "sort": "DESC",
            "sort_field": "id",
            "limit": limit,
            "offset": offset,
        }

        while True:
            json_data["offset"] = offset
            chunk_res = await self.client.request(
                "POST",
                "/face-manager/api/v1/faces/search",
                json_data=json_data,
            )

            if not chunk_res:
                break

            result.extend(
                [
                    PersonFullName(
                        id=person.get("id"),
                        last_name=person.get("last_name"),
                        first_name=person.get("first_name"),
                        middle_name=person.get("middle_name"),
                    )
                    for person in chunk_res
                ]
            )
            offset += limit

        return result

    async def get_all_vehicles(self) -> list[VehicleInfo]:
        """Fetch all vehicles from the plate registry with pagination.

        Returns:
            List of VehicleInfo dicts.
        """

        limit = 500
        offset = 0
        result = []
        json_data = {
            "sort": "DESC",
            "sort_field": "id",
            "limit": limit,
            "offset": offset,
        }

        while True:
            json_data["offset"] = offset
            chunk_res = await self.client.request(
                "POST",
                "/edge-api/api/v1/plates/search",
                json_data=json_data,
            )

            if not chunk_res:
                break

            result.extend(
                [
                    VehicleInfo(id=vehicle.get("id"), number=vehicle.get("number"))
                    for vehicle in chunk_res
                ]
            )
            offset += limit

        return result

    async def get_all_locations(self) -> list[LocationInfo]:
        """Fetch all locations from VMS with pagination, deduplicating by ID.

        Returns:
            List of LocationInfo dicts with ``id`` and ``address`` keys.
        """

        limit = 500
        offset = 0
        result: dict[int | str, dict[str, Any]] = {}
        json_data = {
            "sort": "DESC",
            "sort_field": "id",
            "limit": limit,
            "offset": offset,
        }

        while True:
            json_data["offset"] = offset
            chunk_res = await self.client.request(
                "POST",
                "/edge-api/api/v1/locations/search",
                json_data=json_data,
            )

            if not chunk_res:
                break

            for location in chunk_res:
                location_id = location.get("id")
                address = (location.get("address", {}) or {}).get("string_value")
                key = location_id if location_id is not None else address

                if key is None:
                    continue

                result[key] = {"id": location_id, "address": address}

            offset += limit

        return list(result.values())

    async def fetch_media(
        self, path: str, request_id: str | None = None
    ) -> tuple[bytes, str | None]:
        """Fetch raw media bytes from VMS by relative or absolute path.

        Args:
            path: Relative VMS path or absolute URL.
            request_id: Optional correlation ID for tracing.

        Returns:
            Tuple of raw bytes and content type or None.
        """

        return await self.client.request_binary("GET", path, request_id=request_id)

    @staticmethod
    def _normalize_reference_list(response: Any) -> list[dict[str, Any]]:
        """Normalize a VMS reference list response to a flat list of dicts.

        Handles both raw list responses and ``{"data": [...]}`` envelopes.
        """

        if isinstance(response, list):
            return response

        if isinstance(response, dict):
            data = response.get("data", [])
            return data if isinstance(data, list) else []

        return []
