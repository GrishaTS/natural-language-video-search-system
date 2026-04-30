from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode

from src.core.config import settings
from src.infra.vms.schemas import EventFilter, PersonEventFilter, VehicleEventFilter


@dataclass
class VmsPersonLink:
    """A labelled VMS frontend URL for a single resolved person."""

    label: str
    url: str


def _enum_value(v) -> str:
    """Return the string value of an enum or the string representation of any other type."""

    return v.value if hasattr(v, "value") else str(v)


def _to_ms(iso_str: str | None) -> str:
    """Convert an ISO 8601 datetime string to a millisecond Unix timestamp string."""

    if not iso_str:
        return ""

    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return str(int(dt.timestamp() * 1000))

    except Exception:
        return ""


def build_vms_link(event_filter: EventFilter, channel_ids: list[str]) -> str:
    """Build a VMS frontend event-search URL from a filter and channel IDs.

    Args:
        event_filter: The event filter used for the search.
        channel_ids: VMS channel ID strings to include as location filters.

    Returns:
        Full URL string to the VMS frontend events page.
    """

    base = f"{settings.VMS_FRONTEND_URL}/#/events"
    params: list[tuple[str, str]] = []
    search_data: dict = {}
    features: list[str] = []
    gender: str | None = None

    if isinstance(event_filter, PersonEventFilter):
        params.append(("tab", "persons"))
        params.append(("orderType", "DESC"))
        params.append(("field", "id"))
        attrs = event_filter.face.attributes if event_filter.face else None

        if attrs:
            if attrs.age and attrs.age[0]:
                age = attrs.age[0]
                params.append(
                    ("age", f"{age.lower_bound or ''}:{age.upper_bound or ''}")
                )

            if attrs.genders and attrs.genders[0]:
                gender = _enum_value(attrs.genders[0])

            if attrs.races and attrs.races[0]:
                params.append(("race", _enum_value(attrs.races[0])))

            for attr_name in ("glasses", "beard", "hat", "mask"):
                values = getattr(attrs, attr_name, None)

                if values and values[0]:
                    features.append(_enum_value(values[0]))

    elif isinstance(event_filter, VehicleEventFilter):
        params.append(("tab", "vehicle"))
        params.append(("orderType", "DESC"))
        params.append(("field", "id"))

        if event_filter.plate and event_filter.plate.number:
            search_data["plate"] = event_filter.plate.number

        if event_filter.person:
            if event_filter.person.first_name:
                search_data["firstName"] = event_filter.person.first_name

            if event_filter.person.last_name:
                search_data["lastName"] = event_filter.person.last_name

            if event_filter.person.middle_name:
                search_data["middleName"] = event_filter.person.middle_name

        if event_filter.car_brands:
            for brand in event_filter.car_brands:
                params.append(("carBrands", _enum_value(brand)))

        if event_filter.colors:
            for color in event_filter.colors:
                params.append(("vehicleColor", _enum_value(color)))

        if event_filter.object_types:
            for obj_type in event_filter.object_types:
                params.append(("vehicleType", _enum_value(obj_type)))

    else:
        params.append(("tab", "all"))

    if gender:
        params.append(("gender", gender))

    for feature in features:
        params.append(("features", feature))

    if search_data:
        params.append(
            (
                "searchData",
                json.dumps(search_data, ensure_ascii=False, separators=(",", ":")),
            )
        )

    if event_filter.since or event_filter.until:
        params.append(
            ("timerange", f"{_to_ms(event_filter.since)}:{_to_ms(event_filter.until)}")
        )

    for ch in channel_ids:
        params.append(("locations", ch))

    if event_filter.tag and event_filter.tag.ids:
        for tag_id in event_filter.tag.ids:
            params.append(("tags", str(tag_id)))

    return f"{base}?{urlencode(params, doseq=True)}" if params else base


def build_vms_links_for_persons(
    event_filter: PersonEventFilter,
    channel_ids: list[str],
    resolved_persons: list,
) -> list[VmsPersonLink]:
    """Build one VMS link per resolved person, each with firstName/lastName in searchData.

    Common params (tab, attributes, timerange, locations, tags) are shared across all links.
    Each link gets its own searchData with the person's name.
    """

    base = f"{settings.VMS_FRONTEND_URL}/#/events"
    common_params: list[tuple[str, str]] = [
        ("tab", "persons"),
        ("orderType", "DESC"),
        ("field", "id"),
    ]
    attrs = event_filter.face.attributes if event_filter.face else None
    features: list[str] = []

    if attrs:
        if attrs.age and attrs.age[0]:
            age = attrs.age[0]
            common_params.append(
                ("age", f"{age.lower_bound or ''}:{age.upper_bound or ''}")
            )

        if attrs.genders and attrs.genders[0]:
            common_params.append(("gender", _enum_value(attrs.genders[0])))

        if attrs.races and attrs.races[0]:
            common_params.append(("race", _enum_value(attrs.races[0])))

        for attr_name in ("glasses", "beard", "hat", "mask"):
            values = getattr(attrs, attr_name, None)

            if values and values[0]:
                features.append(_enum_value(values[0]))

    for feature in features:
        common_params.append(("features", feature))

    if event_filter.since or event_filter.until:
        common_params.append(
            ("timerange", f"{_to_ms(event_filter.since)}:{_to_ms(event_filter.until)}")
        )

    for ch in channel_ids:
        common_params.append(("locations", ch))

    if event_filter.tag and event_filter.tag.ids:
        for tag_id in event_filter.tag.ids:
            common_params.append(("tags", str(tag_id)))

    links: list[VmsPersonLink] = []

    for person in resolved_persons:
        search_data: dict = {}

        if getattr(person, "first_name", None):
            search_data["firstName"] = person.first_name

        if getattr(person, "last_name", None):
            search_data["lastName"] = person.last_name

        if getattr(person, "middle_name", None):
            search_data["middleName"] = person.middle_name

        params = list(common_params)

        if search_data:
            params.append(
                (
                    "searchData",
                    json.dumps(search_data, ensure_ascii=False, separators=(",", ":")),
                )
            )

        url = f"{base}?{urlencode(params, doseq=True)}" if params else base
        links.append(VmsPersonLink(label=person.value, url=url))

    return links
