from __future__ import annotations

import asyncio
from typing import AsyncIterator

from langchain_core.messages import HumanMessage
from langgraph.types import Command
from loguru import logger
from src.infra.minio.conversational_search import ConversationalSearchMinioRepository
from src.infra.postgres.conversational_search import ChatRepository
from src.infra.postgres.database import postgres_client
from src.infra.postgres.langgraph import langgraph_checkpointer
from src.infra.vms import VmsAPI
from src.services.conversational_search.graph import build_graph

_GRAPH_TIMEOUT = 300


class ConversationalSearchService:
    """Facade for the LangGraph conversational search pipeline."""

    def __init__(self) -> None:
        self._graph_builder = build_graph()

    async def stream(
        self,
        chat_id: str,
        user_id: str,
        query: str,
        image_bytes: bytes | None = None,
        image_content_type: str = "image/jpeg",
    ) -> AsyncIterator[dict]:
        """Save the user message and run the LangGraph pipeline, yielding SSE events.

        Event types yielded:
        - ``{"type": "stage", "stage": "parsing|resolution|face_resolution|respond"}``
        - ``{"type": "text", "content": token}`` for LLM token chunks.
        - ``{"type": "interrupt", "resolution_id": ..., "entity_type": ..., "options": [...]}``
        - ``{"type": "previews", "vms_link": ..., "event_previews": [...]}``
        - ``{"type": "done", ...}``
        - ``{"type": "error", "content": message}``

        Args:
            chat_id: UUID of the chat thread used as LangGraph thread_id.
            user_id: UUID of the authenticated user.
            query: User text query.
            image_bytes: Optional photo bytes for face-based search.
            image_content_type: MIME type of the image, defaulting to ``image/jpeg``.

        Yields:
            SSE event dicts.
        """

        logger.info(
            f"stream: start chat_id={chat_id}, user_id={user_id}, has_image={image_bytes is not None}, query_len={len(query or '')}"
        )

        image_key: str | None = None
        face_descriptor: dict | None = None

        if image_bytes:
            minio_repo = ConversationalSearchMinioRepository()
            vms = VmsAPI()
            image_key = await minio_repo.upload_chat_image(
                chat_id,
                image_bytes,
                content_type=image_content_type,
            )
            face_descriptor = await vms.get_face_descriptor(image_bytes)
            logger.info(f"stream: uploaded image_key={image_key}, got face_descriptor")

        user_payload = {"image_key": image_key} if image_key else None

        async with postgres_client() as session:
            repo = ChatRepository(session)
            await repo.add_message(
                chat_id=chat_id,
                role="user",
                message_type="dialog",
                content=query or "",
                payload=user_payload,
            )
            await session.commit()

        config = {"configurable": {"thread_id": chat_id}}
        assistant_text_parts: list[str] = []
        vms_link: str | None = None
        vms_links: list[dict] | None = None
        vms_request: dict | None = None
        event_previews: list[dict] = []

        async with langgraph_checkpointer() as checkpointer:
            app = self._graph_builder.compile(checkpointer=checkpointer)

            try:
                async with asyncio.timeout(_GRAPH_TIMEOUT):
                    graph_input: dict = {
                        "messages": [HumanMessage(content=query or "")],
                        "face_descriptor": face_descriptor,
                    }

                    async for event in app.astream_events(
                        input=graph_input,
                        config=config,
                        version="v2",
                    ):

                        event_type = event.get("event", "")
                        name = event.get("name", "")
                        data = event.get("data", {})

                        if event_type == "on_chain_start" and name in (
                            "parsing_node",
                            "entity_resolution_search_node",
                            "face_resolution_search_node",
                            "respond_node",
                        ):

                            stage_map = {
                                "parsing_node": "parsing",
                                "entity_resolution_search_node": "resolution",
                                "face_resolution_search_node": "face_resolution",
                                "respond_node": "respond",
                            }
                            logger.info(f"stream: SSE stage={stage_map[name]}")
                            yield {"type": "stage", "stage": stage_map[name]}

                        elif (
                            event_type == "on_chat_model_stream"
                            and event.get("metadata", {}).get("langgraph_node")
                            == "respond_node"
                        ):

                            chunk = data.get("chunk")

                            if chunk and hasattr(chunk, "content") and chunk.content:
                                token = chunk.content
                                assistant_text_parts.append(token)
                                yield {"type": "text", "content": token}

                        elif (
                            event_type == "on_chain_end" and name == "no_entities_node"
                        ):

                            output = data.get("output", {})

                            if isinstance(output, dict):
                                msgs = output.get("messages", [])

                                if msgs:
                                    guidance = (
                                        msgs[-1].content
                                        if hasattr(msgs[-1], "content")
                                        else str(msgs[-1])
                                    )
                                    assistant_text_parts.append(guidance)
                                    yield {"type": "text", "content": guidance}

                        elif event_type == "on_chain_end" and name == "respond_node":
                            output = data.get("output", {})

                            if isinstance(output, dict):
                                vms_link = output.get("vms_link")
                                vms_links = output.get("vms_links")
                                raw_request = output.get("vms_request")
                                vms_request = (
                                    raw_request.model_dump()
                                    if hasattr(raw_request, "model_dump")
                                    else raw_request
                                )
                                previews_raw = output.get("latest_events_preview", [])
                                event_previews = [
                                    p.model_dump() if hasattr(p, "model_dump") else p
                                    for p in previews_raw
                                ]

                            yield {
                                "type": "previews",
                                "vms_link": vms_link,
                                "vms_links": vms_links,
                                "event_previews": event_previews,
                            }

                        elif event_type == "on_chain_end" and name == "LangGraph":
                            if assistant_text_parts:
                                full_text = "".join(assistant_text_parts)

                                async with postgres_client() as session:
                                    repo = ChatRepository(session)
                                    await repo.add_message(
                                        chat_id=chat_id,
                                        role="assistant",
                                        message_type="dialog",
                                        content=full_text,
                                        payload={
                                            "vms_link": vms_link,
                                            "vms_links": vms_links,
                                            "vms_request": vms_request,
                                            "event_previews": event_previews,
                                        },
                                    )
                                    await session.commit()

                                assistant_text_parts.clear()

                            logger.info(
                                f"stream: done chat_id={chat_id}, vms_link={vms_link}, previews={len(event_previews)}"
                            )
                            yield {
                                "type": "done",
                                "vms_link": vms_link,
                                "vms_links": vms_links,
                                "vms_request": vms_request,
                                "event_previews": event_previews,
                            }

                        elif event_type == "on_chain_stream":
                            chunk = data.get("chunk", {})

                            if isinstance(chunk, dict) and "__interrupt__" in chunk:
                                interrupts = chunk["__interrupt__"]

                                if interrupts:
                                    interrupt_data = (
                                        interrupts[0].value
                                        if hasattr(interrupts[0], "value")
                                        else interrupts[0]
                                    )
                                    logger.info(
                                        f"stream: interrupt entity_type={interrupt_data.get('entity_type')}, entity_value={interrupt_data.get('entity_value')!r}, options_count={len(interrupt_data.get('options', []))}"
                                    )

                                    async with postgres_client() as session:
                                        repo = ChatRepository(session)
                                        await repo.add_message(
                                            chat_id=chat_id,
                                            role="assistant",
                                            message_type="options",
                                            content=f"Уточните: {interrupt_data.get('entity_value', '')}",
                                            payload=interrupt_data,
                                        )
                                        await session.commit()

                                    yield {
                                        "type": "interrupt",
                                        "resolution_id": interrupt_data.get(
                                            "resolution_id"
                                        ),
                                        "entity_value": interrupt_data.get(
                                            "entity_value"
                                        ),
                                        "entity_type": interrupt_data.get(
                                            "entity_type"
                                        ),
                                        "selection_mode": interrupt_data.get(
                                            "selection_mode", "single"
                                        ),
                                        "options": interrupt_data.get("options", []),
                                    }
                                    return

            except asyncio.TimeoutError:
                logger.warning(
                    f"stream timeout after {_GRAPH_TIMEOUT}s: chat_id={chat_id}"
                )
                yield {
                    "type": "error",
                    "content": "Превышено время ожидания. Попробуйте снова.",
                }
                return

        if assistant_text_parts:
            full_text = "".join(assistant_text_parts)

            async with postgres_client() as session:
                repo = ChatRepository(session)
                await repo.add_message(
                    chat_id=chat_id,
                    role="assistant",
                    message_type="dialog",
                    content=full_text,
                    payload={
                        "vms_link": vms_link,
                        "vms_links": vms_links,
                        "vms_request": vms_request,
                        "event_previews": event_previews,
                    },
                )
                await session.commit()

    async def resume(
        self,
        chat_id: str,
        user_id: str,
        resolution_id: str,
        selected_ids: list[str],
    ) -> AsyncIterator[dict]:
        """Resume the graph after the user resolved an entity interrupt.

        Records the user's selection, resumes the LangGraph thread via ``Command(resume=...)``, and yields the same SSE event types as ``stream()``.

        Args:
            chat_id: UUID of the chat thread.
            user_id: UUID of the authenticated user.
            resolution_id: ID from the original interrupt payload.
            selected_ids: IDs of the options the user chose.

        Yields:
            SSE event dicts.
        """

        async with postgres_client() as session:
            repo = ChatRepository(session)
            labels = await repo.set_options_selected_ids(
                chat_id, resolution_id, selected_ids
            )
            user_content = ", ".join(labels) if labels else "Выбор подтвержден"
            await repo.add_message(
                chat_id=chat_id,
                role="user",
                message_type="dialog",
                content=user_content,
            )
            await session.commit()

        logger.info(
            f"resume: start chat_id={chat_id}, resolution_id={resolution_id}, selected_ids={selected_ids}"
        )
        config = {"configurable": {"thread_id": chat_id}}
        assistant_text_parts: list[str] = []
        vms_link: str | None = None
        vms_links: list[dict] | None = None
        vms_request: dict | None = None
        event_previews: list[dict] = []
        resume_value = {"resolution_id": resolution_id, "selected_ids": selected_ids}

        async with langgraph_checkpointer() as checkpointer:
            app = self._graph_builder.compile(checkpointer=checkpointer)

            try:
                async with asyncio.timeout(_GRAPH_TIMEOUT):
                    async for event in app.astream_events(
                        input=Command(resume=resume_value),
                        config=config,
                        version="v2",
                    ):

                        event_type = event.get("event", "")
                        name = event.get("name", "")
                        data = event.get("data", {})

                        if event_type == "on_chain_start" and name in (
                            "entity_resolution_apply_node",
                            "face_resolution_apply_node",
                            "respond_node",
                        ):

                            stage_map = {
                                "entity_resolution_apply_node": "resolution",
                                "face_resolution_apply_node": "face_resolution",
                                "respond_node": "respond",
                            }
                            logger.info(f"resume: SSE stage={stage_map[name]}")
                            yield {"type": "stage", "stage": stage_map[name]}

                        elif (
                            event_type == "on_chat_model_stream"
                            and event.get("metadata", {}).get("langgraph_node")
                            == "respond_node"
                        ):

                            chunk = data.get("chunk")

                            if chunk and hasattr(chunk, "content") and chunk.content:
                                token = chunk.content
                                assistant_text_parts.append(token)
                                yield {"type": "text", "content": token}

                        elif event_type == "on_chain_end" and name == "respond_node":
                            output = data.get("output", {})

                            if isinstance(output, dict):
                                vms_link = output.get("vms_link")
                                vms_links = output.get("vms_links")
                                raw_request = output.get("vms_request")
                                vms_request = (
                                    raw_request.model_dump()
                                    if hasattr(raw_request, "model_dump")
                                    else raw_request
                                )
                                previews_raw = output.get("latest_events_preview", [])
                                event_previews = [
                                    p.model_dump() if hasattr(p, "model_dump") else p
                                    for p in previews_raw
                                ]

                            yield {
                                "type": "previews",
                                "vms_link": vms_link,
                                "vms_links": vms_links,
                                "event_previews": event_previews,
                            }

                        elif event_type == "on_chain_end" and name == "LangGraph":
                            if assistant_text_parts:
                                full_text = "".join(assistant_text_parts)

                                async with postgres_client() as session:
                                    repo = ChatRepository(session)
                                    await repo.add_message(
                                        chat_id=chat_id,
                                        role="assistant",
                                        message_type="dialog",
                                        content=full_text,
                                        payload={
                                            "vms_link": vms_link,
                                            "vms_links": vms_links,
                                            "vms_request": vms_request,
                                            "event_previews": event_previews,
                                        },
                                    )
                                    await session.commit()

                                assistant_text_parts.clear()

                            logger.info(
                                f"resume: done chat_id={chat_id}, vms_link={vms_link}, previews={len(event_previews)}"
                            )
                            yield {
                                "type": "done",
                                "vms_link": vms_link,
                                "vms_links": vms_links,
                                "vms_request": vms_request,
                                "event_previews": event_previews,
                            }

                        elif event_type == "on_chain_stream":
                            chunk = data.get("chunk", {})

                            if isinstance(chunk, dict) and "__interrupt__" in chunk:
                                interrupts = chunk["__interrupt__"]

                                if interrupts:
                                    interrupt_data = (
                                        interrupts[0].value
                                        if hasattr(interrupts[0], "value")
                                        else interrupts[0]
                                    )
                                    logger.info(
                                        f"resume: interrupt entity_type={interrupt_data.get('entity_type')}, entity_value={interrupt_data.get('entity_value')!r}, options_count={len(interrupt_data.get('options', []))}"
                                    )

                                    async with postgres_client() as session:
                                        repo = ChatRepository(session)
                                        await repo.add_message(
                                            chat_id=chat_id,
                                            role="assistant",
                                            message_type="options",
                                            content=f"Уточните: {interrupt_data.get('entity_value', '')}",
                                            payload=interrupt_data,
                                        )
                                        await session.commit()

                                    yield {
                                        "type": "interrupt",
                                        "resolution_id": interrupt_data.get(
                                            "resolution_id"
                                        ),
                                        "entity_value": interrupt_data.get(
                                            "entity_value"
                                        ),
                                        "entity_type": interrupt_data.get(
                                            "entity_type"
                                        ),
                                        "selection_mode": interrupt_data.get(
                                            "selection_mode", "single"
                                        ),
                                        "options": interrupt_data.get("options", []),
                                    }
                                    return

            except asyncio.TimeoutError:
                logger.warning(
                    f"resume timeout after {_GRAPH_TIMEOUT}s: chat_id={chat_id}"
                )
                yield {
                    "type": "error",
                    "content": "Превышено время ожидания. Попробуйте снова.",
                }
                return

        if assistant_text_parts:
            full_text = "".join(assistant_text_parts)

            async with postgres_client() as session:
                repo = ChatRepository(session)
                await repo.add_message(
                    chat_id=chat_id,
                    role="assistant",
                    message_type="dialog",
                    content=full_text,
                    payload={
                        "vms_link": vms_link,
                        "vms_links": vms_links,
                        "vms_request": vms_request,
                        "event_previews": event_previews,
                    },
                )
                await session.commit()
