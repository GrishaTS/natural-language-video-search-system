from src.services.conversational_search.usecases.event_filter_builder import EventFilterBuilder
from src.services.conversational_search.schemas.query import (
    PeopleQuerySchema,
    VehiclesQuerySchema,
    AllQuerySchema,
    TimeRange,
    PersonQuery,
    VehiclePlateQuery,
    FaceAttributesQuery,
    AgeRangeQuery,
)
from src.infra.vms.schemas import PersonEventFilter, VehicleEventFilter, AllEventFilter
from src.domain.entity import ResolvedEntity
from src.domain.enums import EntityType


def _person_entity(entity_id: str, value: str) -> ResolvedEntity:
    return ResolvedEntity(entity_type=EntityType.PERSON, value=value, entity_id=entity_id)


def _vehicle_entity(value: str) -> ResolvedEntity:
    return ResolvedEntity(entity_type=EntityType.VEHICLE, value=value, entity_id="0")


# ── PEOPLE domain ─────────────────────────────────────────────────────────────

def test_people_with_entity_builds_face_ids():
    qs = PeopleQuerySchema(
        domain="PEOPLE",
        persons=[PersonQuery(name="Петров", query_text="Петров")],
        addresses=[], floors=[], time_range=None, face_attributes=None, is_refinement=False,
    )
    entities = [_person_entity("42", "Иван Петров")]
    result = EventFilterBuilder.build(qs, entities, channel_ids=[], tag_ids=[])
    assert isinstance(result, PersonEventFilter)
    assert result.face is not None
    assert result.face.face_ids == [42]


def test_people_with_time_range():
    qs = PeopleQuerySchema(
        domain="PEOPLE", persons=[], addresses=[], floors=[],
        time_range=TimeRange(since="2026-03-01T00:00:00Z", until="2026-03-31T23:59:59Z"),
        face_attributes=None, is_refinement=False,
    )
    result = EventFilterBuilder.build(qs, [], channel_ids=[], tag_ids=[])
    assert isinstance(result, PersonEventFilter)
    assert result.since == "2026-03-01T00:00:00Z"
    assert result.until == "2026-03-31T23:59:59Z"


def test_people_with_channel_ids():
    qs = PeopleQuerySchema(
        domain="PEOPLE", persons=[], addresses=[], floors=[],
        time_range=None, face_attributes=None, is_refinement=False,
    )
    result = EventFilterBuilder.build(qs, [], channel_ids=[101, 202], tag_ids=[])
    assert isinstance(result, PersonEventFilter)
    assert result.channel is not None
    assert set(result.channel.ids) == {101, 202}


def test_people_with_face_attributes():
    fa = FaceAttributesQuery(
        age=[AgeRangeQuery(lower_bound=25, upper_bound=30)],
        beard=["with_beard"],
        glasses=["with_glasses"],
    )
    qs = PeopleQuerySchema(
        domain="PEOPLE", persons=[], addresses=[], floors=[],
        time_range=None, face_attributes=fa, is_refinement=False,
    )
    result = EventFilterBuilder.build(qs, [], channel_ids=[], tag_ids=[])
    assert isinstance(result, PersonEventFilter)
    assert result.face is not None
    assert result.face.attributes.age[0].lower_bound == 25
    assert result.face.attributes.age[0].upper_bound == 30
    assert result.face.attributes.beard == ["with_beard"]
    assert result.face.attributes.glasses == ["with_glasses"]


def test_people_with_face_attributes_normalizes_empty_lists_to_none():
    fa = FaceAttributesQuery(
        age=[AgeRangeQuery(lower_bound=25, upper_bound=30)],
        genders=[],
        beard=["with_beard"],
        glasses=["with_glasses"],
        races=[],
        hat=[],
        mask=[],
    )
    qs = PeopleQuerySchema(
        domain="PEOPLE", persons=[], addresses=[], floors=[],
        time_range=None, face_attributes=fa, is_refinement=False,
    )
    result = EventFilterBuilder.build(qs, [], channel_ids=[], tag_ids=[])

    assert isinstance(result, PersonEventFilter)
    assert result.face is not None
    assert result.face.attributes is not None
    assert result.face.attributes.genders is None
    assert result.face.attributes.races is None
    assert result.face.attributes.hat is None
    assert result.face.attributes.mask is None
    assert result.face.attributes.beard == ["with_beard"]
    assert result.face.attributes.glasses == ["with_glasses"]


def test_people_empty_returns_person_filter_no_face():
    qs = PeopleQuerySchema(
        domain="PEOPLE", persons=[], addresses=[], floors=[],
        time_range=None, face_attributes=None, is_refinement=False,
    )
    result = EventFilterBuilder.build(qs, [], channel_ids=[], tag_ids=[])
    assert isinstance(result, PersonEventFilter)
    assert result.face is None


# ── VEHICLES domain ───────────────────────────────────────────────────────────

def test_vehicles_with_plate_entity():
    qs = VehiclesQuerySchema(
        domain="VEHICLES",
        plates=[VehiclePlateQuery(plate="АА123ББ", query_text="АА123ББ")],
        addresses=[], floors=[], time_range=None,
        car_brands=None, colors=None, object_types=None, is_refinement=False,
    )
    entities = [_vehicle_entity("АА123ББ")]
    result = EventFilterBuilder.build(qs, entities, channel_ids=[], tag_ids=[])
    assert isinstance(result, VehicleEventFilter)
    assert result.plate is not None
    assert result.plate.number == "АА123ББ"


def test_vehicles_with_brands_colors_types():
    qs = VehiclesQuerySchema(
        domain="VEHICLES", plates=[], addresses=[], floors=[],
        time_range=TimeRange(since="2025-01-01T00:00:00Z", until="2025-12-31T23:59:59Z"),
        car_brands=["MERCEDES_BENZ"],
        colors=["yellow"],
        object_types=["bus"],
        is_refinement=False,
    )
    result = EventFilterBuilder.build(qs, [], channel_ids=[], tag_ids=[])
    assert isinstance(result, VehicleEventFilter)
    assert result.car_brands == ["MERCEDES_BENZ"]
    assert result.colors == ["yellow"]
    assert result.object_types == ["bus"]
    assert result.since == "2025-01-01T00:00:00Z"
    assert result.until == "2025-12-31T23:59:59Z"


# ── ALL domain ────────────────────────────────────────────────────────────────

def test_all_domain_with_channels():
    qs = AllQuerySchema(
        domain="ALL", addresses=[], floors=[],
        time_range=TimeRange(since="2026-04-03T00:00:00Z", until="2026-04-03T23:59:59Z"),
        is_refinement=False,
    )
    result = EventFilterBuilder.build(qs, [], channel_ids=[1, 2, 3], tag_ids=[])
    assert isinstance(result, AllEventFilter)
    assert result.channel.ids == [1, 2, 3]


def test_none_query_schema_returns_all_filter():
    result = EventFilterBuilder.build(None, [], channel_ids=[], tag_ids=[])
    assert isinstance(result, AllEventFilter)
