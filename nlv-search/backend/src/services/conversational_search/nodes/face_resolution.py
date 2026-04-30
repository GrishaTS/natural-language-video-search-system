from __future__ import annotations

from uuid import uuid4

from langgraph.types import interrupt
from loguru import logger
from src.infra.vms import VmsAPI
from src.services.conversational_search.state import (
    ConversationState,
    FaceCandidate,
    FaceResolution,
)


async def face_prep_node(state: ConversationState) -> dict[str, object]:
    """Strip persons from query_schema when photo is present.

    Prevents entity_resolution_search_node from resolving text persons
    in parallel with photo-based face resolution.
    """

    qs = state.get("query_schema")

    if qs is not None and hasattr(qs, "persons") and qs.persons:
        qs = qs.model_copy(update={"persons": []})
        logger.info(
            f"face_prep: stripped {len(state['query_schema'].persons)} persons from query_schema"
        )
        return {"query_schema": qs}

    return {}


async def face_resolution_search_node(state: ConversationState) -> dict[str, object]:
    """Search VMS face-manager for similar faces by descriptor.

    Reads:  face_descriptor
    Writes: face_candidates
    """

    descriptor = state["face_descriptor"]
    vms = VmsAPI()
    faces = await vms.search_faces_by_descriptor(descriptor)
    candidates = [
        FaceCandidate(
            id=f["id"],
            value=" ".join(
                filter(None, [f.get("first_name"), f.get("last_name")])
            ).strip()
            or f"ID {f['id']}",
            first_name=f.get("first_name"),
            last_name=f.get("last_name"),
            middle_name=f.get("middle_name"),
        )
        for f in faces
        if f.get("id")
    ]
    logger.info(f"face_resolution_search -> {len(candidates)} candidates")
    return {"face_candidates": candidates}


async def face_resolution_apply_node(state: ConversationState) -> dict[str, object]:
    """Interrupt user to choose from face candidates or 'search by photo'.

    Selection mode is multi. User can pick multiple persons OR 'Искать по фотографии',
    but not both.
    Reads:  face_candidates, face_descriptor
    Writes: face_resolution, face_candidates=[]
    """

    candidates = state.get("face_candidates", [])
    options = [{"id": str(c.id), "value": c.value} for c in candidates]
    options.append({"id": "__by_descriptor__", "value": "Искать по фотографии"})
    user_choice = interrupt(
        {
            "resolution_id": str(uuid4()),
            "entity_value": "фотография",
            "entity_type": "face",
            "selection_mode": "multi",
            "options": options,
        }
    )
    selected_ids = (
        user_choice.get("selected_ids", []) if isinstance(user_choice, dict) else []
    )
    has_descriptor = "__by_descriptor__" in selected_ids
    person_ids = [sid for sid in selected_ids if sid != "__by_descriptor__"]

    if has_descriptor and person_ids:
        raise ValueError(
            "Нельзя одновременно выбрать 'Искать по фотографии' и конкретных людей"
        )

    if has_descriptor:
        resolution = FaceResolution(
            mode="by_descriptor",
            descriptor=state["face_descriptor"],
        )
        logger.info("face_resolution_apply -> by_descriptor")

    else:
        matched = [c for c in candidates if str(c.id) in person_ids]
        resolution = FaceResolution(
            mode="by_ids",
            face_ids=[c.id for c in matched],
            person_names=[c.value for c in matched],
        )
        logger.info(f"face_resolution_apply -> by_ids: {resolution.face_ids}")

    return {"face_resolution": resolution, "face_candidates": []}
