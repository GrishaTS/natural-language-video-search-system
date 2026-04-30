from langchain_core.messages import HumanMessage

from src.services.conversational_search.graph import initial_router, route_after_parsing
from src.services.conversational_search.schemas.query import (
    PeopleQuerySchema,
    TimeRange,
    VehiclesQuerySchema,
    PersonQuery,
    VehiclePlateQuery,
)
from src.domain.entity import ResolvedEntity
from src.domain.enums import EntityType


def _people_qs(**kwargs) -> PeopleQuerySchema:
    defaults = dict(domain="PEOPLE", persons=[], addresses=[], floors=[], time_range=None,
                    face_attributes=None, is_refinement=False)
    defaults.update(kwargs)
    return PeopleQuerySchema(**defaults)


def _vehicles_qs(**kwargs) -> VehiclesQuerySchema:
    defaults = dict(domain="VEHICLES", plates=[], addresses=[], floors=[], time_range=None,
                    car_brands=None, colors=None, object_types=None, is_refinement=False)
    defaults.update(kwargs)
    return VehiclesQuerySchema(**defaults)


# ── initial_router ────────────────────────────────────────────────────────────

def test_initial_router_has_text():
    state = {"messages": [HumanMessage(content="найди Петрова")], "face_descriptor": None}
    assert initial_router(state) == "has_text"


def test_initial_router_photo_only():
    state = {"messages": [HumanMessage(content="")], "face_descriptor": b"\x00\x01"}
    assert initial_router(state) == "photo_only"


def test_initial_router_text_and_photo_goes_has_text():
    state = {"messages": [HumanMessage(content="найди")], "face_descriptor": b"\x00\x01"}
    assert initial_router(state) == "has_text"


# ── route_after_parsing ───────────────────────────────────────────────────────

def test_route_needs_resolution_persons():
    qs = _people_qs(persons=[PersonQuery(name="Петров", query_text="Петров")])
    state = {"query_schema": qs, "face_descriptor": None, "face_resolution": None, "selected_entities": []}
    assert route_after_parsing(state) == "needs_resolution"


def test_route_skip_resolution_time_range():
    qs = _people_qs(time_range=TimeRange(since="2026-01-01T00:00:00Z", until="2026-01-31T23:59:59Z"))
    state = {"query_schema": qs, "face_descriptor": None, "face_resolution": None, "selected_entities": []}
    assert route_after_parsing(state) == "skip_resolution"


def test_route_skip_resolution_existing_context():
    qs = _people_qs()
    state = {
        "query_schema": qs,
        "face_descriptor": None,
        "face_resolution": None,
        "selected_entities": [
            ResolvedEntity(entity_type=EntityType.PERSON, value="Петров Иван", entity_id="1")
        ],
    }
    assert route_after_parsing(state) == "skip_resolution"


def test_route_no_entities_empty_schema():
    qs = _people_qs()
    state = {"query_schema": qs, "face_descriptor": None, "face_resolution": None, "selected_entities": []}
    assert route_after_parsing(state) == "no_entities"


def test_route_no_entities_none_schema():
    state = {"query_schema": None, "face_descriptor": None, "face_resolution": None, "selected_entities": []}
    assert route_after_parsing(state) == "no_entities"


def test_route_has_face():
    qs = _people_qs()
    state = {"query_schema": qs, "face_descriptor": b"\x00\x01", "face_resolution": None, "selected_entities": []}
    assert route_after_parsing(state) == "has_face"


def test_route_vehicles_plates_needs_resolution():
    qs = _vehicles_qs(plates=[VehiclePlateQuery(plate="АА123ББ", query_text="АА123ББ")])
    state = {"query_schema": qs, "face_descriptor": None, "face_resolution": None, "selected_entities": []}
    assert route_after_parsing(state) == "needs_resolution"
