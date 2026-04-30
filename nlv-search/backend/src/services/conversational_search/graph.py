from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from loguru import logger
from src.services.conversational_search.nodes.face_resolution import (
    face_prep_node,
    face_resolution_apply_node,
    face_resolution_search_node,
)
from src.services.conversational_search.nodes.parsing import parsing_node
from src.services.conversational_search.nodes.resolution import (
    entity_resolution_apply_node,
    entity_resolution_search_node,
)
from src.services.conversational_search.nodes.respond import respond_node
from src.services.conversational_search.state import ConversationState


def initial_router(state: ConversationState) -> str:
    """Route based on whether input has text, photo, or both."""

    has_face = bool(state.get("face_descriptor"))
    has_text = bool((state["messages"][-1].content or "").strip())
    route = "photo_only" if has_face and not has_text else "has_text"
    logger.info(f"initial_router: has_face={has_face}, has_text={has_text} -> {route}")
    return route


def route_after_parsing(state: ConversationState) -> str:
    """

    "has_face"         — photo present → face_prep_node
    "needs_resolution" — named entities → entity_resolution
    "skip_resolution"  — filters or existing context → respond directly
    "no_entities"      — nothing useful extracted
    """

    if state.get("face_descriptor"):
        logger.info("route_after_parsing -> has_face")
        return "has_face"

    qs = state.get("query_schema")

    if qs is None:
        logger.info("route_after_parsing -> no_entities (query_schema=None)")
        return "no_entities"

    has_named = bool(
        getattr(qs, "persons", [])
        or getattr(qs, "plates", [])
        or getattr(qs, "addresses", [])
    )
    has_filters = bool(
        getattr(qs, "time_range", None)
        or getattr(qs, "floors", [])
        or getattr(qs, "face_attributes", None)
        or getattr(qs, "car_brands", None)
        or getattr(qs, "colors", None)
        or getattr(qs, "object_types", None)
    )
    has_existing_context = bool(
        state.get("face_resolution") or state.get("selected_entities")
    )
    logger.info(
        f"route_after_parsing: has_named={has_named}, has_filters={has_filters}, has_existing_context={has_existing_context}"
    )

    if has_named:
        logger.info("route_after_parsing -> needs_resolution")
        return "needs_resolution"

    if has_filters or has_existing_context:
        logger.info("route_after_parsing -> skip_resolution")
        return "skip_resolution"

    logger.info("route_after_parsing -> no_entities")
    return "no_entities"


def route_after_face_resolution(state: ConversationState) -> str:
    """After face resolution: resolve addresses if present, else respond."""

    qs = state.get("query_schema")

    if qs and getattr(qs, "addresses", []):
        logger.info("route_after_face_resolution -> needs_address_resolution")
        return "needs_address_resolution"

    logger.info("route_after_face_resolution -> respond")
    return "respond"


async def _no_entities_node(state: ConversationState) -> dict:
    """Return guidance message when query has no searchable entities."""

    guidance = (
        "Уточните запрос: укажите имя человека, номер автомобиля, адрес или атрибуты поиска. "
        "Например: 'Покажи Иванова на Платонова 20б за январь' или 'Синий BMW вчера'."
    )
    return {"messages": [AIMessage(content=guidance)]}


def build_graph() -> StateGraph:
    """Build and return the configured LangGraph StateGraph for conversational search.

    The graph wires together parsing, entity resolution, face resolution, and respond nodes with conditional routing based on query content.

    Returns:
        Compiled-ready StateGraph. Call ``.compile(checkpointer=...)`` to run it.
    """

    graph = StateGraph(ConversationState)

    graph.add_node("parsing_node", parsing_node)
    graph.add_node("face_prep_node", face_prep_node)
    graph.add_node("face_resolution_search_node", face_resolution_search_node)
    graph.add_node("face_resolution_apply_node", face_resolution_apply_node)
    graph.add_node("entity_resolution_search_node", entity_resolution_search_node)
    graph.add_node("entity_resolution_apply_node", entity_resolution_apply_node)
    graph.add_node("respond_node", respond_node)
    graph.add_node("no_entities_node", _no_entities_node)

    graph.add_conditional_edges(
        START,
        initial_router,
        {
            "has_text": "parsing_node",
            "photo_only": "face_resolution_search_node",
        },
    )

    graph.add_conditional_edges(
        "parsing_node",
        route_after_parsing,
        {
            "has_face": "face_prep_node",
            "no_entities": "no_entities_node",
            "skip_resolution": "respond_node",
            "needs_resolution": "entity_resolution_search_node",
        },
    )

    graph.add_edge("face_prep_node", "face_resolution_search_node")
    graph.add_edge("face_resolution_search_node", "face_resolution_apply_node")
    graph.add_conditional_edges(
        "face_resolution_apply_node",
        route_after_face_resolution,
        {
            "needs_address_resolution": "entity_resolution_search_node",
            "respond": "respond_node",
        },
    )

    graph.add_edge("entity_resolution_search_node", "entity_resolution_apply_node")
    graph.add_edge("entity_resolution_apply_node", "respond_node")

    graph.add_edge("no_entities_node", END)
    graph.add_edge("respond_node", END)
    return graph
