from __future__ import annotations

import asyncio
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt
from loguru import logger
from src.domain.entity import ResolvedEntity
from src.infra.ai import AIEmbedAPI, EmbedRequest
from src.infra.ai.langchain import get_langchain_llm
from src.infra.qdrant.conversational_search import ConversationalSearchQdrantRepository
from src.prompts.conversational_search.resolution import get_resolution_system_prompt
from src.services.conversational_search.schemas.resolution import (
    AutoResolve,
    EntityDecision,
    ResolutionOutput,
)
from src.services.conversational_search.state import (
    Candidate,
    ConversationState,
    SearchCandidates,
)
from src.services.conversational_search.utils import llm_retry


def _build_candidates_message(
    qs, search_candidates: SearchCandidates, user_query: str = ""
) -> str:
    """Format candidates for LLM resolution prompt. Uses positional keys only — no real IDs."""

    lines: list[str] = []

    if user_query:
        lines.append(f'Original user query: "{user_query}"\n')

    lines.append("Resolve the following entities:\n")
    persons = getattr(qs, "persons", [])

    for pq in persons:
        lines.append(f'Person query_text="{pq.query_text}" (name="{pq.name}"):')

        for i, c in enumerate(search_candidates.persons):
            lines.append(f"  p{i}: {c.value}")

        lines.append("")

    addresses = getattr(qs, "addresses", [])

    for aq in addresses:
        lines.append(f'Address query_text="{aq.query_text}" (value="{aq.value}"):')

        for i, c in enumerate(search_candidates.addresses):
            lines.append(f"  a{i}: {c.value}")

        lines.append("")

    plates = getattr(qs, "plates", [])

    for vq in plates:
        lines.append(f'Vehicle query_text="{vq.query_text}" (plate="{vq.plate}"):')

        for i, c in enumerate(search_candidates.vehicles):
            lines.append(f"  v{i}: {c.value}")

        lines.append("")

    return "\n".join(lines)


_SELECTION_MODE: dict[str, str] = {
    "address": "multi",
    "person": "multi",
    "vehicle": "single",
}


def _detect_entity_type(entity_value: str, qs) -> str:
    """Detect entity_type by matching entity_value against query items."""

    for pq in getattr(qs, "persons", []):
        if pq.query_text == entity_value or pq.name == entity_value:
            return "person"

    for aq in getattr(qs, "addresses", []):
        if aq.query_text == entity_value or aq.value == entity_value:
            return "address"

    for vq in getattr(qs, "plates", []):
        if vq.query_text == entity_value or vq.plate == entity_value:
            return "vehicle"

    return "person"


async def entity_resolution_search_node(state: ConversationState) -> dict[str, object]:
    """

    Step 1 of entity resolution: embedding + Qdrant search + LLM decision.
    Saves result to state["resolution_context"] so the apply node can use it
    without repeating this work on resume after interrupt.
    Reads:  query_schema
    Writes: resolution_context, search_candidates=None
    """

    qs = state["query_schema"]
    ai_embed = AIEmbedAPI()
    qdrant_repo = ConversationalSearchQdrantRepository()
    persons = getattr(qs, "persons", [])
    addresses = getattr(qs, "addresses", [])
    plates = getattr(qs, "plates", [])
    logger.info(
        f"entity_resolution_search: persons={len(persons)}, addresses={len(addresses)}, plates={len(plates)}"
    )

    async def embed_text(text: str) -> list[float]:
        """Embed a single entity string for vector search."""

        resp = await ai_embed.embed(EmbedRequest(texts=[text]))
        return resp.embeddings[0]

    async def search_persons() -> list[Candidate]:
        """Search Qdrant for all person candidates referenced by the query."""

        if not persons:
            return []

        tasks = [embed_text(pq.name) for pq in persons]
        vectors = await asyncio.gather(*tasks)
        seen: dict[str, Candidate] = {}

        for vec in vectors:
            hits = await qdrant_repo.search_people(vec, top_k=10)

            for h in hits:
                if h["id"] not in seen:
                    seen[h["id"]] = Candidate(
                        id=h["id"],
                        value=h["value"],
                        score=h["score"],
                        first_name=h.get("first_name"),
                        last_name=h.get("last_name"),
                        middle_name=h.get("middle_name"),
                    )

        return list(seen.values())

    async def search_addresses() -> list[Candidate]:
        """Search Qdrant for all address candidates referenced by the query."""

        if not addresses:
            return []

        tasks = [embed_text(aq.value) for aq in addresses]
        vectors = await asyncio.gather(*tasks)
        seen: dict[str, Candidate] = {}

        for vec in vectors:
            hits = await qdrant_repo.search_locations(vec, top_k=10)

            for h in hits:
                if h["id"] not in seen:
                    seen[h["id"]] = Candidate(
                        id=h["id"], value=h["value"], score=h["score"]
                    )

        return list(seen.values())

    async def search_vehicles() -> list[Candidate]:
        """Search Qdrant for all vehicle candidates referenced by the query."""

        if not plates:
            return []

        tasks = [embed_text(vq.plate) for vq in plates]
        vectors = await asyncio.gather(*tasks)
        seen: dict[str, Candidate] = {}

        for vec in vectors:
            hits = await qdrant_repo.search_vehicles(vec, top_k=10)

            for h in hits:
                if h["id"] not in seen:
                    seen[h["id"]] = Candidate(
                        id=h["id"], value=h["value"], score=h["score"]
                    )

        return list(seen.values())

    person_candidates, address_candidates, vehicle_candidates = await asyncio.gather(
        search_persons(), search_addresses(), search_vehicles()
    )
    logger.info(
        f"entity_resolution_search: found person_candidates={len(person_candidates)}, address_candidates={len(address_candidates)}, vehicle_candidates={len(vehicle_candidates)}"
    )
    search_candidates = SearchCandidates(
        persons=person_candidates,
        addresses=address_candidates,
        vehicles=vehicle_candidates,
    )

    key_map: dict[str, Candidate] = {}

    for i, c in enumerate(search_candidates.persons):
        key_map[f"p{i}"] = c

    for i, c in enumerate(search_candidates.addresses):
        key_map[f"a{i}"] = c

    for i, c in enumerate(search_candidates.vehicles):
        key_map[f"v{i}"] = c

    llm = get_langchain_llm()
    structured_llm = llm.with_structured_output(
        ResolutionOutput, method="function_calling"
    )
    system_prompt = get_resolution_system_prompt()
    user_query = str(state["messages"][-1].content) if state.get("messages") else ""
    candidates_message = _build_candidates_message(
        qs, search_candidates, user_query=user_query
    )
    clean_candidates_message = "; ".join(str(candidates_message).split("\n"))
    logger.info(
        f"resolution <- len(system_prompt)={len(system_prompt)}, clean_candidates_message={clean_candidates_message}"
    )

    @llm_retry
    async def _invoke() -> ResolutionOutput:
        """Invoke the structured entity resolution LLM."""

        return await structured_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=candidates_message),
            ]
        )

    result: ResolutionOutput = await _invoke()
    logger.info(
        f"entity_resolution_search: LLM decisions count={len(result.decisions)}"
    )
    clean_result_decisions = "; ".join(str(result.decisions).split("\n"))
    logger.info(f"entity_resolution_search: decisions={clean_result_decisions}")

    return {
        "resolution_context": {
            "key_map": {k: c.model_dump() for k, c in key_map.items()},
            "decisions": [d.model_dump() for d in result.decisions],
        },
        "search_candidates": None,
    }


async def entity_resolution_apply_node(state: ConversationState) -> dict[str, object]:
    """

    Step 2 of entity resolution: apply LLM decisions, interrupt for UserResolve.
    On resume after interrupt, LangGraph re-runs only THIS node — the expensive
    search_node is NOT re-executed because it already completed and saved to state.
    Reads:  resolution_context, query_schema
    Writes: selected_entities, resolution_context=None
    """

    qs = state["query_schema"]
    ctx = state["resolution_context"] or {}
    key_map: dict[str, Candidate] = {
        k: Candidate(**v) for k, v in ctx.get("key_map", {}).items()
    }
    id_to_candidate: dict[str, Candidate] = {c.id: c for c in key_map.values()}
    decisions: list[EntityDecision] = [
        EntityDecision(**d) for d in ctx.get("decisions", [])
    ]
    auto_resolved: list[ResolvedEntity] = []
    logger.info(f"entity_resolution_apply: processing {len(decisions)} decisions")

    for decision in decisions:
        entity_type = _detect_entity_type(decision.entity_value, qs)

        if isinstance(decision.decision, AutoResolve):
            logger.info(
                f"entity_resolution_apply: AutoResolve entity_value={decision.entity_value!r}, keys={decision.decision.selected_ids}"
            )

            for key in dict.fromkeys(decision.decision.selected_ids):
                candidate = key_map.get(key)

                if candidate is None:
                    logger.warning(
                        f"resolution apply: unknown key {key!r} in AutoResolve, skipping"
                    )
                    continue

                logger.info(
                    f"entity_resolution_apply: auto-resolved {entity_type} -> {candidate.value!r} (id={candidate.id})"
                )
                auto_resolved.append(
                    ResolvedEntity(
                        entity_type=entity_type,
                        entity_id=candidate.id,
                        value=candidate.value,
                        first_name=candidate.first_name,
                        last_name=candidate.last_name,
                        middle_name=candidate.middle_name,
                    )
                )

        else:
            logger.info(
                f"entity_resolution_apply: UserResolve interrupt entity_value={decision.entity_value!r}, entity_type={entity_type}"
            )
            options = [
                {"id": key_map[k].id, "value": key_map[k].value}
                for k in dict.fromkeys(decision.decision.filtered_options)
                if k in key_map
            ]
            user_choice = interrupt(
                {
                    "resolution_id": str(uuid4()),
                    "entity_value": decision.entity_value,
                    "entity_type": entity_type,
                    "selection_mode": _SELECTION_MODE.get(entity_type, "single"),
                    "options": options,
                }
            )

            if user_choice and isinstance(user_choice, dict):
                selected_ids = user_choice.get("selected_ids", [])

                for selected_id in selected_ids:
                    candidate = id_to_candidate.get(selected_id)

                    if candidate is None:
                        logger.warning(
                            f"resolution apply: unknown id {selected_id!r} after resume, skipping"
                        )
                        continue

                    auto_resolved.append(
                        ResolvedEntity(
                            entity_type=entity_type,
                            entity_id=selected_id,
                            value=candidate.value,
                            first_name=candidate.first_name,
                            last_name=candidate.last_name,
                            middle_name=candidate.middle_name,
                        )
                    )

    logger.info(
        f"entity_resolution_apply: done, selected_entities={[e.value for e in auto_resolved]}"
    )
    return {
        "selected_entities": auto_resolved,
        "resolution_context": None,
    }
