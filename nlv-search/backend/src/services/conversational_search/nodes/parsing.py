from __future__ import annotations

import warnings
from datetime import datetime, timezone

from langchain_core.messages import SystemMessage
from loguru import logger
from src.infra.ai.langchain import get_langchain_llm
from src.prompts.conversational_search.parsing import get_parsing_system_prompt
from src.services.conversational_search.schemas.query import ParsedQuery
from src.services.conversational_search.state import ConversationState
from src.services.conversational_search.utils import llm_retry


async def parsing_node(state: ConversationState) -> dict[str, object]:
    """

    Reads: messages[-1] (HumanMessage), query_schema (prev for refinement),

           selected_entities (prev), latest_summary (prev)

    Writes: {"query_schema": QuerySchema}
    """

    llm = get_langchain_llm()
    structured_llm = llm.with_structured_output(
        ParsedQuery, method="json_schema", strict=True
    )
    prev_query_schema = state.get("query_schema")
    prev_selected_entities = state.get("selected_entities", [])
    prev_latest_summary = state.get("latest_summary")
    prev_query_dict = None

    if prev_query_schema is not None:
        if hasattr(prev_query_schema, "model_dump"):
            prev_query_dict = prev_query_schema.model_dump()

    prev_entities_list = None

    if prev_selected_entities:
        prev_entities_list = [
            {"entity_type": e.entity_type, "value": e.value}
            for e in prev_selected_entities
        ]

    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    current_date = now_utc.strftime("%Y-%m-%d")
    current_datetime_utc = now_utc.isoformat().replace("+00:00", "Z")
    has_face = bool(state.get("face_descriptor"))
    system_prompt = get_parsing_system_prompt(
        prev_query_schema=prev_query_dict,
        prev_selected_entities=prev_entities_list,
        prev_latest_summary=prev_latest_summary,
        current_date=current_date,
        current_datetime_utc=current_datetime_utc,
        has_face=has_face,
    )
    last_message = state["messages"][-1]
    clean_system_prompt = "; ".join(system_prompt.split("\n"))
    clean_last_message = "; ".join((str(last_message).split("\n")))
    logger.info(
        f'parsing <- clean_system_prompt="{clean_system_prompt}", clean_last_message={clean_last_message}'
    )

    @llm_retry
    async def _invoke() -> ParsedQuery:
        """Invoke the structured parsing LLM with warning suppression."""

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
            return await structured_llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    last_message,
                ]
            )

    wrapper: ParsedQuery = await _invoke()
    qs = wrapper.query
    logger.info(
        f"parsing -> type={type(qs).__name__}, is_refinement={qs.is_refinement}"
    )
    logger.info(f"parsing -> query_schema={qs}")
    updates: dict[str, object] = {"query_schema": qs}

    if not qs.is_refinement:
        logger.info(
            "parsing: is_refinement=False — clear face_resolution + selected_entities"
        )
        updates["face_resolution"] = None
        updates["selected_entities"] = []

    return updates
