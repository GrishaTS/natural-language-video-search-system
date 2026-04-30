from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from loguru import logger
from src.infra.ai.langchain import get_langchain_llm
from src.infra.vms import VmsAPI
from src.infra.vms.schemas import PersonEventFilter
from src.prompts.conversational_search.respond import get_respond_system_prompt
from src.services.conversational_search.state import (
    ConversationState,
    EventPreview,
    FaceResolution,
)
from src.services.conversational_search.usecases.event_filter_builder import (
    EventFilterBuilder,
)
from src.services.conversational_search.usecases.event_summarizer import EventSummarizer
from src.services.conversational_search.usecases.vms_link_builder import (
    build_vms_link,
    build_vms_links_for_persons,
)
from src.services.conversational_search.usecases.vms_search import VmsSearchService
from src.services.conversational_search.utils import llm_retry


def _normalize_snapshot_url(raw_url: str) -> str:
    """Strip scheme+host from absolute VMS snapshot URLs, keeping only path+query.

    The frontend proxies snapshots through /api/v1/media/snapshot/{path}, which
    requires a relative path. VMS may return absolute URLs like
    http://vms-host/api/v1/media/snapshot/uuid?ttl=300 — we normalise them here
    so the stored snapshot_url is always relative.
    """

    if raw_url.startswith("http://") or raw_url.startswith("https://"):
        parsed = urlparse(raw_url)
        return f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path

    return raw_url


def _get_event_snapshot_url(event: dict) -> str | None:
    """Extract the best available snapshot URL from a VMS event.

    VMS events have a `snapshots` list containing objects with `type` (FULLSCREEN/THUMBNAIL),
    `path`, and optionally `original_quality_snapshot`. We prefer FULLSCREEN original_quality,
    then FULLSCREEN path, then any snapshot's original_quality_snapshot, then any path.
    """

    snapshots = event.get("snapshots") or []
    fullscreen = next((s for s in snapshots if s.get("type") == "FULLSCREEN"), None)

    if fullscreen:
        return (
            fullscreen.get("original_quality_snapshot")
            or fullscreen.get("path")
            or None
        )

    for s in snapshots:
        oqs = s.get("original_quality_snapshot")

        if oqs:
            return oqs

    for s in snapshots:
        path = s.get("path")

        if path:
            return path

    return None


def _build_respond_human_message(
    summary: Any,
    selected_entities: list,
    face_resolution: Any | None = None,
) -> str:
    """Format the LLM human message from the VMS summary and resolved context.

    Args:
        summary: Typed summary object such as PeopleSummary, VehicleSummary, or AllSummary.
        selected_entities: Resolved entity list for narrative context.
        face_resolution: Optional face resolution mode for narrative context.

    Returns:
        Formatted string to send as the HumanMessage to the LLM.
    """

    entities_str = (
        ", ".join(e.value for e in selected_entities) if selected_entities else "нет"
    )
    face_info = ""

    if face_resolution:
        if face_resolution.mode == "by_ids" and face_resolution.person_names:
            face_info = f"Face search: по персонам из реестра — {', '.join(face_resolution.person_names)}\n\n"

        elif face_resolution.mode == "by_descriptor":
            face_info = "Face search: по фотографии (поиск по дескриптору лица)\n\n"

    return (
        f"Search results:\n{json.dumps(summary.model_dump() if hasattr(summary, 'model_dump') else summary, ensure_ascii=False, default=str)}\n\n"
        f"Resolved entities: {entities_str}\n\n"
        f"{face_info}"
        "Write a narrative answer in Russian based on the search results above."
    )


async def respond_node(state: ConversationState) -> dict[str, object]:
    """Execute VMS event search and generate a narrative answer.

    Step 1 (Python):

      1. Resolve address strings to VMS channel IDs.
      2. Resolve floor numbers to VMS tag IDs.
      3. Build ``EventFilter`` from query schema and resolved entities.
      4. Search VMS events.
      5. Summarize events into a typed summary object.
      6. Build VMS frontend links.
      7. Extract top event previews.

    Step 2 (LLM, streaming):

      Invoke the LLM to generate a Russian-language narrative response.

    Args:
        state: Current conversation state.

    Returns:
        State update dict with messages, VMS request/link data, summary, and previews.
    """

    query_schema = state.get("query_schema")
    selected_entities = state.get("selected_entities", [])
    face_resolution = state.get("face_resolution")
    vms_search = VmsSearchService()

    resolved_address_values = list(
        dict.fromkeys(e.value for e in selected_entities if e.entity_type == "address")
    )
    address_values = resolved_address_values or (
        [aq.value for aq in getattr(query_schema, "addresses", [])]
        if query_schema
        else []
    )
    logger.info(
        f"respond_node: address_values={address_values} (resolved={bool(resolved_address_values)}), selected_entities={[e.value for e in selected_entities]}, face_resolution={face_resolution}"
    )
    channels = await vms_search.get_channels_by_addresses(address_values)
    channel_ids = [
        ch["resource_id"] for ch in channels if ch.get("resource_id") is not None
    ]
    logger.info(f"respond_node: channel_ids={channel_ids}")

    floors = list(getattr(query_schema, "floors", [])) if query_schema else []
    tag_ids = await vms_search.get_tag_ids_by_floor_numbers(floors)
    logger.info(f"respond_node: floors={floors}, tag_ids={tag_ids}")

    event_filter = EventFilterBuilder.build(
        query_schema,
        selected_entities,
        channel_ids,
        tag_ids,
        face_resolution=face_resolution,
    )
    logger.info(f"respond_node: event_filter={event_filter}")

    events = await vms_search.search_events(event_filter)
    logger.info(f"respond_node: search_events returned {len(events)} events")

    summarizer = EventSummarizer()
    summary = summarizer.summarize(events, event_filter)

    link_channel_ids = [str(ch.get("id", ch.get("resource_id", ""))) for ch in channels]
    person_entities = [
        e
        for e in selected_entities
        if e.entity_type == "person" and (e.first_name or e.last_name)
    ]

    if isinstance(event_filter, PersonEventFilter) and person_entities:
        per_person_links = build_vms_links_for_persons(
            event_filter, link_channel_ids, person_entities
        )
        vms_links: list[dict] | None = [
            {"label": lnk.label, "url": lnk.url} for lnk in per_person_links
        ]
        vms_link = per_person_links[0].url

    else:
        vms_link = build_vms_link(event_filter, link_channel_ids)
        vms_links = None

    logger.info(
        f"respond_node: vms_link={vms_link}, vms_links_count={len(vms_links) if vms_links else 0}"
    )

    sorted_events = sorted(
        [e for e in events if e.get("start_time") and _get_event_snapshot_url(e)],
        key=lambda e: e["start_time"],
        reverse=True,
    )
    latest_events_preview = [
        EventPreview(
            event_id=str(e.get("id", "")),
            snapshot_url=_normalize_snapshot_url(_get_event_snapshot_url(e)),
            timestamp=datetime.fromtimestamp(
                e["start_time"] / 1000, tz=timezone.utc
            ).isoformat(),
        )
        for e in sorted_events[:3]
    ]

    llm = get_langchain_llm()
    system_prompt = get_respond_system_prompt()
    human_message_content = _build_respond_human_message(
        summary, selected_entities, face_resolution
    )

    @llm_retry
    async def _invoke():
        """Invoke the response LLM for the narrative answer."""

        return await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_message_content),
            ]
        )

    response = await _invoke()
    clean_human_message_content = "; ".join(str(human_message_content).split("\n"))
    logger.info(
        f'respond(len(system_prompt)={len(system_prompt)}, input="{clean_human_message_content}") -> {response.content}'
    )
    narrative_text = response.content if hasattr(response, "content") else str(response)
    latest_summary_str = (
        narrative_text if isinstance(narrative_text, str) else str(narrative_text)
    )
    return {
        "messages": [AIMessage(content=latest_summary_str)],
        "vms_request": event_filter,
        "vms_link": vms_link,
        "vms_links": vms_links,
        "latest_summary": latest_summary_str,
        "latest_events_preview": latest_events_preview,
    }
