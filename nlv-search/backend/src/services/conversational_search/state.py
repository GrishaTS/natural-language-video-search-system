from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from src.domain.entity import (
    ResolvedEntity,
)
from src.infra.vms.schemas import EventFilter
from src.services.conversational_search.schemas.query import (
    AllQuerySchema,
    PeopleQuerySchema,
    VehiclesQuerySchema,
)


class Candidate(BaseModel):
    """A single entity resolution candidate returned from Qdrant search."""

    id: str
    value: str
    score: float

    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None


class SearchCandidates(BaseModel):
    """Grouped Qdrant search results for all entity types in one resolution pass."""

    persons: list[Candidate] = []
    addresses: list[Candidate] = []
    vehicles: list[Candidate] = []


class EventPreview(BaseModel):
    """Lightweight preview of a VMS event for frontend display."""

    event_id: str
    snapshot_url: str
    timestamp: str


class FaceCandidate(BaseModel):
    """A person candidate returned from VMS face-manager search by descriptor."""

    id: int
    value: str
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None


class FaceResolution(BaseModel):
    """Resolved face search strategy: either by registered face IDs or by descriptor."""

    mode: Literal["by_ids", "by_descriptor"]
    face_ids: list[int] = []
    person_names: list[str] = []
    descriptor: dict | None = None


class ConversationState(TypedDict):
    """LangGraph state dictionary for the conversational search pipeline.

    Persisted between graph turns via the LangGraph checkpointer. Fields marked transient are cleared after their producing node completes.
    """

    messages: Annotated[list[BaseMessage], add_messages]

    query_schema: PeopleQuerySchema | VehiclesQuerySchema | AllQuerySchema | None

    resolution_context: dict | None

    selected_entities: list[ResolvedEntity]
    search_candidates: SearchCandidates | None

    vms_request: EventFilter | None
    vms_link: str | None
    vms_links: list[dict] | None
    latest_summary: str | None
    latest_events_preview: list[EventPreview]

    face_descriptor: dict | None
    face_candidates: list[FaceCandidate]
    face_resolution: FaceResolution | None
