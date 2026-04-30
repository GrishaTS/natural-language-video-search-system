from __future__ import annotations

from src.domain.entity import ResolvedEntity
from src.infra.vms.schemas import (
    AgeParams,
    AllEventFilter,
    ChannelFilter,
    EventFilter,
    FaceAttributes,
    FaceDescriptorItem,
    FaceDescriptorVersion,
    FaceFilter,
    FaceMatchFilter,
    PersonEventFilter,
    PlateFilter,
    TagFilter,
    VehicleEventFilter,
)
from src.services.conversational_search.schemas.query import (
    PeopleQuerySchema,
    QuerySchema,
    VehiclesQuerySchema,
)
from src.services.conversational_search.state import FaceResolution


def _build_channel_filter(channel_ids: list[int]) -> ChannelFilter | None:
    """Build a ChannelFilter from a list of channel resource IDs, or None if empty."""

    if not channel_ids:
        return None

    return ChannelFilter(ids=channel_ids)


def _build_tag_filter(tag_ids: list[int]) -> TagFilter | None:
    """Build a TagFilter from a list of tag IDs, or None if empty."""

    if not tag_ids:
        return None

    return TagFilter(ids=tag_ids)


def _build_plate_filter(selected_entities: list[ResolvedEntity]) -> PlateFilter | None:
    """Return a PlateFilter for the first resolved vehicle entity, or None."""

    for e in selected_entities:
        if e.entity_type == "vehicle":
            return PlateFilter(number=e.value)

    return None


def _build_face_attributes(qs: PeopleQuerySchema) -> FaceAttributes | None:
    """Build FaceAttributes from a PeopleQuerySchema, or None if no attributes are set."""

    fa = qs.face_attributes

    if not fa:
        return None

    age_params = None

    if fa.age:
        age_params = [
            AgeParams(lower_bound=a.lower_bound, upper_bound=a.upper_bound)
            for a in fa.age
        ]

    has_data = bool(
        age_params
        or fa.genders
        or fa.beard
        or fa.glasses
        or fa.races
        or fa.hat
        or fa.mask
    )

    if not has_data:
        return None

    return FaceAttributes(
        age=age_params,
        genders=fa.genders or None,
        beard=fa.beard or None,
        glasses=fa.glasses or None,
        races=fa.races or None,
        hat=fa.hat or None,
        mask=fa.mask or None,
    )


def _build_face_ids_from_entities(selected_entities: list[ResolvedEntity]) -> list[int]:
    """Extract face IDs from resolved person entities."""

    return [int(e.entity_id) for e in selected_entities if e.entity_type == "person"]


class EventFilterBuilder:
    """Deterministic assembly of EventFilter from QuerySchema + resolved entities + IDs."""

    @staticmethod
    def build(
        query_schema: QuerySchema | None,
        selected_entities: list[ResolvedEntity],
        channel_ids: list[int],
        tag_ids: list[int],
        face_resolution: FaceResolution | None = None,
    ) -> EventFilter:
        """Build the appropriate EventFilter subtype from query context.

        Dispatches to PersonEventFilter, VehicleEventFilter, or AllEventFilter based on query_schema type and face_resolution presence.

        Args:
            query_schema: Parsed query. None produces AllEventFilter.
            selected_entities: Resolved entity list from entity resolution.
            channel_ids: VMS channel resource IDs from address resolution.
            tag_ids: VMS tag IDs from floor resolution.
            face_resolution: Face resolution strategy, overriding text-based person search.

        Returns:
            Concrete EventFilter instance ready for VMS API.
        """

        channel = _build_channel_filter(channel_ids)
        tag = _build_tag_filter(tag_ids)
        since = (
            query_schema.time_range.since
            if query_schema and query_schema.time_range
            else None
        )
        until = (
            query_schema.time_range.until
            if query_schema and query_schema.time_range
            else None
        )

        face_attrs = None

        if query_schema and isinstance(query_schema, PeopleQuerySchema):
            face_attrs = _build_face_attributes(query_schema)

        if face_resolution:
            if face_resolution.mode == "by_ids":
                return PersonEventFilter(
                    channel=channel,
                    tag=tag,
                    since=since,
                    until=until,
                    face=FaceFilter(
                        face_ids=face_resolution.face_ids,
                        attributes=face_attrs,
                    ),
                )

            else:
                desc = face_resolution.descriptor
                return PersonEventFilter(
                    channel=channel,
                    tag=tag,
                    since=since,
                    until=until,
                    face=FaceFilter(attributes=face_attrs) if face_attrs else None,
                    face_match=FaceMatchFilter(
                        descriptors=[
                            [
                                FaceDescriptorItem(
                                    descriptor=desc["descriptor"],
                                    version=FaceDescriptorVersion(**desc["version"]),
                                )
                            ]
                        ],
                    ),
                )

        if query_schema is None:
            return AllEventFilter(channel=channel, tag=tag, since=since, until=until)

        if isinstance(query_schema, PeopleQuerySchema):
            face_ids = _build_face_ids_from_entities(selected_entities)
            face_filter = None

            if face_ids or face_attrs:
                face_filter = FaceFilter(
                    face_ids=face_ids or None,
                    attributes=face_attrs,
                )

            return PersonEventFilter(
                channel=channel,
                tag=tag,
                since=since,
                until=until,
                face=face_filter,
            )

        if isinstance(query_schema, VehiclesQuerySchema):
            return VehicleEventFilter(
                channel=channel,
                tag=tag,
                since=since,
                until=until,
                plate=_build_plate_filter(selected_entities),
                car_brands=query_schema.car_brands,
                colors=query_schema.colors,
                object_types=query_schema.object_types,
            )

        return AllEventFilter(
            channel=channel,
            tag=tag,
            since=since,
            until=until,
        )
