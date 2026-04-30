from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from src.infra.vms.schemas import Domain, EventFilter
from src.services.conversational_search.usecases.summary_schemas import (
    AllEvents,
    AllMetrics,
    AllSummary,
    ChannelEntry,
    ChannelStats,
    EventTypeEntry,
    FaceIdentityStats,
    IdentifiedPersonEntry,
    LocationEntry,
    LocationStats,
    PeopleAttributes,
    PeopleMetrics,
    PeopleSummary,
    PlateEntry,
    PlateStats,
    QueryContext,
    TagEntry,
    TagStats,
    VehicleAttributes,
    VehicleMetrics,
    VehicleSummary,
    WatchlistEntry,
)


def _build_query_context(event_filter: EventFilter, events: list[Any]) -> QueryContext:
    """Derive QueryContext metadata from the filter and matched events."""

    channel_map = {
        e["channel_id"]: e["channel_name"] for e in events if "channel_id" in e
    }
    filter_channel_ids = event_filter.channel.ids if event_filter.channel else []
    channel_names = list(
        {channel_map[cid] for cid in (filter_channel_ids or []) if cid in channel_map}
    )
    tag_map = {t["id"]: t["name"] for e in events for t in e.get("tags", [])}
    filter_tag_ids = event_filter.tag.ids if event_filter.tag else []
    tag_names = list({tag_map[tid] for tid in (filter_tag_ids or []) if tid in tag_map})
    person_name: str | None = None
    plate_number: str | None = None

    if hasattr(event_filter, "person") and event_filter.person:
        person_name = (
            " ".join(
                filter(
                    None,
                    [event_filter.person.first_name, event_filter.person.last_name],
                )
            )
            or None
        )

    if hasattr(event_filter, "plate") and event_filter.plate:
        plate_number = event_filter.plate.number

    return QueryContext(
        domain=event_filter.domain.value,
        person_name=person_name,
        plate_number=plate_number,
        since=event_filter.since,
        until=event_filter.until,
        channels_searched=len(filter_channel_ids or []),
        channel_names=channel_names,
        tags_searched=len(filter_tag_ids or []),
        tag_names=tag_names,
    )


def _ms_to_iso(ms: int) -> str:
    """Convert a millisecond Unix timestamp to an ISO 8601 string."""

    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def _metrics_base(events: list[Any]) -> tuple[int, str | None, str | None, int]:
    """Compute base event metrics: count, first/last seen ISO strings, and unique day count."""

    if not events:
        return 0, None, None, 0

    timestamps = sorted(e["start_time"] for e in events if e.get("start_time"))

    if not timestamps:
        return len(events), None, None, 0

    unique_days = len(
        {datetime.fromtimestamp(t / 1000, tz=timezone.utc).date() for t in timestamps}
    )
    return (
        len(events),
        _ms_to_iso(timestamps[0]),
        _ms_to_iso(timestamps[-1]),
        unique_days,
    )


def _location_stats(events: list[Any]) -> LocationStats:
    """Aggregate location statistics from event channel addresses."""

    addresses = [
        e.get("channel_address", {}).get("string_value")
        for e in events
        if e.get("channel_address", {}).get("string_value")
    ]
    counter = Counter(addresses)
    top = [LocationEntry(address=a, count=c) for a, c in counter.most_common(3)]
    sorted_evs = sorted(
        [
            e
            for e in events
            if e.get("start_time") and e.get("channel_address", {}).get("string_value")
        ],
        key=lambda e: e["start_time"],
    )
    first_loc = sorted_evs[0]["channel_address"]["string_value"] if sorted_evs else None
    last_loc = sorted_evs[-1]["channel_address"]["string_value"] if sorted_evs else None
    return LocationStats(
        top_locations=top,
        unique_locations=len(counter),
        first_location=first_loc,
        last_location=last_loc,
    )


def _channel_stats(events: list[Any]) -> ChannelStats:
    """Aggregate channel statistics from event channel names."""

    names = [e.get("channel_name") for e in events if e.get("channel_name")]
    counter = Counter(names)
    top = [ChannelEntry(name=n, count=c) for n, c in counter.most_common(3)]
    channel_types = Counter(
        e.get("channel_type") for e in events if e.get("channel_type")
    )
    return ChannelStats(
        top_channels=top,
        unique_channels=len(counter),
        channel_types=dict(channel_types),
    )


def _tag_stats(events: list[Any]) -> TagStats:
    """Aggregate tag statistics from event tag lists."""

    all_tags = [
        tag.get("name") for e in events for tag in e.get("tags", []) if tag.get("name")
    ]
    counter = Counter(all_tags)
    top = [TagEntry(name=n, count=c) for n, c in counter.most_common(5)]
    return TagStats(top_tags=top, unique_tags=len(counter))


def _people_attributes(events: list[Any]) -> PeopleAttributes:
    """Aggregate physical attribute distributions from people events."""

    genders: Counter = Counter()
    ages: list[int] = []
    beards: Counter = Counter()
    glasses_c: Counter = Counter()
    hats: Counter = Counter()
    masks: Counter = Counter()
    races: Counter = Counter()

    for event in events:
        attrs = event.get("params", {}).get("attributes") or {}

        if gender := attrs.get("gender"):
            genders[gender] += 1

        age = attrs.get("age")

        if age is not None:
            try:
                ages.append(int(age))

            except (ValueError, TypeError):
                pass

        if (b := attrs.get("beard")) is not None:
            beards[str(b)] += 1

        if (g := attrs.get("glasses")) is not None:
            glasses_c[str(g)] += 1

        if (h := attrs.get("hat")) is not None:
            hats[str(h)] += 1

        if (m := attrs.get("mask")) is not None:
            masks[str(m)] += 1

        if race := attrs.get("race"):
            races[race] += 1

    return PeopleAttributes(
        gender_distribution=dict(genders),
        age_avg=round(sum(ages) / len(ages), 1) if ages else None,
        age_min=min(ages) if ages else None,
        age_max=max(ages) if ages else None,
        beard_distribution=dict(beards),
        glasses_distribution=dict(glasses_c),
        hat_distribution=dict(hats),
        mask_distribution=dict(masks),
        race_distribution=dict(races),
    )


def _face_identity_stats(events: list[Any]) -> FaceIdentityStats:
    """Aggregate face identity and watchlist statistics from people events."""

    persons: dict[str, dict] = {}

    watchlists: dict[str, dict] = {}
    identified_count = 0
    all_similarities: list[float] = []

    for event in events:
        face_ids = event.get("face_identities") or []

        if not face_ids or not face_ids[0].get("faces"):
            continue

        identified_count += 1
        best_group = face_ids[0]
        best_face = best_group["faces"][0]
        name = (
            " ".join(
                filter(None, [best_face.get("first_name"), best_face.get("last_name")])
            )
            or "Unknown"
        )
        similarity = best_face.get("similarity", 0.0)
        ts = event.get("start_time")

        if name not in persons:
            persons[name] = {"count": 0, "similarities": [], "timestamps": []}

        persons[name]["count"] += 1
        persons[name]["similarities"].append(similarity)

        if ts:
            persons[name]["timestamps"].append(ts)

        all_similarities.append(similarity)
        wl = best_group.get("list") or {}
        wl_name = wl.get("name", "Unknown")
        wl_level = wl.get("level", 0)

        if wl_name not in watchlists:
            watchlists[wl_name] = {"count": 0, "level": wl_level}

        watchlists[wl_name]["count"] += 1

    top_persons = sorted(persons.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
    person_entries = []

    for name, data in top_persons:
        timestamps = sorted(data["timestamps"])
        person_entries.append(
            IdentifiedPersonEntry(
                full_name=name,
                count=data["count"],
                avg_similarity=round(
                    sum(data["similarities"]) / len(data["similarities"]), 4
                ),
                first_seen=_ms_to_iso(timestamps[0]) if timestamps else None,
                last_seen=_ms_to_iso(timestamps[-1]) if timestamps else None,
            )
        )

    top_watchlists = sorted(
        watchlists.items(), key=lambda x: x[1]["count"], reverse=True
    )[:3]
    watchlist_entries = [
        WatchlistEntry(list_name=n, count=d["count"], level=d["level"])
        for n, d in top_watchlists
    ]
    return FaceIdentityStats(
        identified_count=identified_count,
        unidentified_count=len(events) - identified_count,
        unique_persons=len(persons),
        top_persons=person_entries,
        top_watchlists=watchlist_entries,
        avg_similarity=(
            round(sum(all_similarities) / len(all_similarities), 4)
            if all_similarities
            else None
        ),
    )


def _plate_number(event: dict) -> str | None:
    """Extract the plate number string from an event params dict, or None."""

    plate = event.get("params", {}).get("plate") or {}
    return plate.get("number") if isinstance(plate, dict) else None


def _plate_stats(events: list[Any]) -> PlateStats:
    """Aggregate license plate statistics from vehicle events."""

    sorted_evs = sorted(
        [e for e in events if e.get("start_time")], key=lambda e: e["start_time"]
    )
    plates = [p for e in events if (p := _plate_number(e))]
    counter = Counter(plates)
    top = [PlateEntry(number=p, count=c) for p, c in counter.most_common(10)]
    first_plate = next((p for e in sorted_evs if (p := _plate_number(e))), None)
    last_plate = None

    for e in sorted_evs:
        if p := _plate_number(e):
            last_plate = p

    return PlateStats(
        top_plates=top,
        unique_plates=len(counter),
        first_plate=first_plate,
        last_plate=last_plate,
    )


def _vehicle_attributes(events: list[Any]) -> VehicleAttributes:
    """Aggregate vehicle brand, color, and type distributions from vehicle events."""

    brands: Counter = Counter()
    colors: Counter = Counter()
    types: Counter = Counter()

    for event in events:
        obj = (event.get("params") or {}).get("object") or {}

        if (
            brand := (obj.get("car_brand") or {}).get("value")
        ) and brand.upper() != "UNKNOWN":

            brands[brand] += 1

        if color := (obj.get("color") or {}).get("value"):
            colors[color] += 1

        if obj_type := (obj.get("object_type") or {}).get("value"):
            types[obj_type] += 1

    return VehicleAttributes(
        brand_distribution=dict(brands),
        color_distribution=dict(colors),
        type_distribution=dict(types),
    )


def _all_metrics(events: list[Any]) -> AllMetrics:
    """Compute cross-domain metrics, categorizing events by type."""

    count, first_seen, last_seen, unique_days = _metrics_base(events)
    face_events = vehicle_events = access_events = object_events = 0

    for event in events:
        topic = event.get("topic") or ""
        module = event.get("module") or ""
        tags = [t.get("name", "") for t in event.get("tags", [])]

        if "Face" in topic or event.get("face_identities"):
            face_events += 1

        elif "Plate" in topic or event.get("params", {}).get("plate"):
            vehicle_events += 1

        elif "Access control" in tags:
            access_events += 1

        elif "ObjectTrack" in module or "ObjectInside" in topic:
            object_events += 1

    other = max(0, count - face_events - vehicle_events - access_events - object_events)
    return AllMetrics(
        events_count=count,
        first_seen=first_seen,
        last_seen=last_seen,
        unique_days=unique_days,
        face_events=face_events,
        vehicle_events=vehicle_events,
        access_events=access_events,
        object_events=object_events,
        other_events=other,
    )


def _all_events(events: list[Any]) -> AllEvents:
    """Count events by topic for the all-domain summary."""

    topic_counter = Counter(e.get("topic") for e in events if e.get("topic"))
    top = [EventTypeEntry(topic=t, count=c) for t, c in topic_counter.most_common(5)]
    return AllEvents(top_event_types=top, unique_event_types=len(topic_counter))


class EventSummarizer:
    """Pure data transformer: raw VMS events → typed summary objects."""

    def summarize(
        self, events: list[Any], event_filter: EventFilter
    ) -> PeopleSummary | VehicleSummary | AllSummary:
        """Build a typed summary from raw VMS events and the originating filter.

        Dispatches to people, vehicle, or all-domain summarization based on event_filter.domain.

        Args:
            events: Raw event dicts from VMS API.
            event_filter: The filter used to retrieve the events.

        Returns:
            Typed summary object matching the filter domain.
        """

        domain = event_filter.domain

        if domain == Domain.PEOPLE:
            return self._summarize_people(events or [], event_filter)

        if domain == Domain.VEHICLE:
            return self._summarize_vehicles(events or [], event_filter)

        return self._summarize_all(events or [], event_filter)

    def _summarize_people(
        self, events: list[Any], event_filter: EventFilter
    ) -> PeopleSummary:
        """Build a PeopleSummary from PEOPLE-domain events."""

        count, first_seen, last_seen, unique_days = _metrics_base(events)
        return PeopleSummary(
            query=_build_query_context(event_filter, events),
            metrics=PeopleMetrics(
                events_count=count,
                first_seen=first_seen,
                last_seen=last_seen,
                unique_days=unique_days,
            ),
            attributes=_people_attributes(events),
            identities=_face_identity_stats(events),
            location=_location_stats(events),
            channels=_channel_stats(events),
            tags=_tag_stats(events),
        )

    def _summarize_vehicles(
        self, events: list[Any], event_filter: EventFilter
    ) -> VehicleSummary:
        """Build a VehicleSummary from VEHICLE-domain events."""

        count, first_seen, last_seen, unique_days = _metrics_base(events)
        plate_events = sum(
            1 for e in events if (e.get("params", {}).get("plate") or e.get("plate"))
        )
        return VehicleSummary(
            query=_build_query_context(event_filter, events),
            metrics=VehicleMetrics(
                events_count=count,
                first_seen=first_seen,
                last_seen=last_seen,
                unique_days=unique_days,
                plate_events=plate_events,
            ),
            plates=_plate_stats(events),
            attributes=_vehicle_attributes(events),
            location=_location_stats(events),
            channels=_channel_stats(events),
            tags=_tag_stats(events),
        )

    def _summarize_all(
        self, events: list[Any], event_filter: EventFilter
    ) -> AllSummary:
        """Build an AllSummary from cross-domain events."""

        return AllSummary(
            query=_build_query_context(event_filter, events),
            metrics=_all_metrics(events),
            events=_all_events(events),
            vehicles=_plate_stats(events),
            location=_location_stats(events),
            channels=_channel_stats(events),
            tags=_tag_stats(events),
        )
