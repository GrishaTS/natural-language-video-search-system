from __future__ import annotations

import asyncio
from typing import Any

from src.infra.vms import EventFilter, VmsAPI


class VmsSearchService:
    """Thin wrapper around VmsAPI for event search and entity lookups."""

    def __init__(self, vms_api: VmsAPI | None = None) -> None:
        """Initialize with an optional VmsAPI instance; defaults to a new VmsAPI()."""

        self.vms_api = vms_api or VmsAPI()

    async def search_events(self, event_filter: EventFilter) -> list[Any]:
        """Search VMS events using the given filter.

        Args:
            event_filter: Structured event filter.

        Returns:
            List of raw event dicts from VMS.
        """

        return await self.vms_api.search_events(event_filter=event_filter)

    async def get_channels_by_addresses(self, addresses: list[str]) -> list[dict]:
        """Return raw channel dicts with both `resource_id` (for EventFilter) and `id` (for links)."""

        cleaned = [a.strip() for a in addresses if a and a.strip()]

        if not cleaned:
            return []

        tasks = [
            self.vms_api.search_locations(address=addr, limit=512) for addr in cleaned
        ]
        results = await asyncio.gather(*tasks)
        seen: set[int] = set()
        channels: list[dict] = []

        for batch in results:
            for ch in batch:
                rid = ch.get("resource_id")

                if rid is not None and rid not in seen and ch.get("type") == "CHANNEL":
                    seen.add(rid)
                    channels.append(ch)

        return channels

    async def get_tag_ids_by_floor_numbers(self, floors: list[int]) -> list[int]:
        """Resolve floor numbers to VMS tag IDs.

        Args:
            floors: List of floor numbers to look up.

        Returns:
            List of VMS tag IDs corresponding to the given floor numbers.
        """

        if not floors:
            return []

        tasks = [
            self.vms_api.search_tags(tag_name=f"Floor {floor}") for floor in floors
        ]
        results = await asyncio.gather(*tasks)
        tag_ids: set[int] = set()

        for tags in results:
            if tags:
                tid = tags[0].get("id")

                if tid is not None:
                    tag_ids.add(tid)

        return list(tag_ids)
