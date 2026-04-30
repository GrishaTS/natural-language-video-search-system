from typing import Any


def get_parsing_system_prompt(
    prev_query_schema: dict | None,
    prev_selected_entities: list | None,
    prev_latest_summary: str | None,
    current_date: str,
    current_datetime_utc: str,
    has_face: bool = False,
) -> str:
    """Build the system prompt for the parsing LLM node.

    Returns:
        Formatted system prompt string.
    """

    context_section = ""

    if prev_query_schema or prev_selected_entities or prev_latest_summary:
        context_section = "\n<conversation_context>\n"

        if prev_query_schema:
            import json

            context_section += f"prev_query_schema: {json.dumps(prev_query_schema, ensure_ascii=False)}\n"

        if prev_selected_entities:
            import json

            context_section += f"prev_selected_entities: {json.dumps(prev_selected_entities, ensure_ascii=False)}\n"

        if prev_latest_summary:
            context_section += f"prev_latest_summary: {prev_latest_summary}\n"

        context_section += "</conversation_context>\n"

    face_photo_section = ""

    if has_face:
        face_photo_section = (
            "\nFACE PHOTO CONTEXT:\n"
            "The user attached a face photo alongside their text message.\n"
            "- Domain MUST be PEOPLE.\n"
            "- persons list MUST be empty [].\n"
            "- Text provides supplemental constraints only — not a standalone query.\n"
            "- Extract face_attributes, addresses, floors, time_range independently from text.\n"
            "- face_attributes and addresses are INDEPENDENT fields: extract BOTH when both are present.\n"
            "- Address extraction from text is REQUIRED even when photo is attached.\n"
            '  EXAMPLE: text="в очках на платонова 20б" → '
            'face_attributes.glasses=["with_glasses"], '
            'addresses=[{"value": "платонова 20б", "query_text": "на платонова 20б"}]\n'
            "- Apply standard time_range rules (including single-day markers) from text.\n"
            "- If text contains nothing extractable — return PeopleQuerySchema with all optional fields null.\n"
        )

    return (
        f"Current date: {current_date}.\n"
        f"Current datetime UTC: {current_datetime_utc}.\n"
        "Convert all relative or partial temporal expressions to absolute ISO 8601 UTC timestamps.\n"
        "Compute precise start and end datetimes based on calendar boundaries (day, week, month, year)\n"
        "or exact rolling windows for sub-day expressions (hour, minute).\n\n"
        "Task: Analyze the user request and extract a structured search query (QuerySchema).\n"
        "Output a valid JSON matching one of: PeopleQuerySchema, VehiclesQuerySchema, AllQuerySchema.\n\n"
        "RULES:\n"
        "1. Determine SEARCH DOMAIN:\n"
        "   PEOPLE — persons, faces, face attributes.\n"
        "   VEHICLES — any vehicle type (car, bus, truck, motorcycle, van, SUV, автомобиль, автобус,\n"
        "   грузовик, мотоцикл, фургон, джип, легковая) or vehicle-specific term (plate, brand, object_type).\n"
        "   A single vehicle-type word is sufficient — do not fall back to ALL when a vehicle type is present.\n"
        "   ALL — generic queries with no domain-specific entity.\n"
        "2. Extract named entities:\n"
        "   - persons: list of PersonQuery(name=normalized_name, query_text=as_written_by_user)\n"
        "     IMPORTANT: abbreviated names like 'Г. Петров', 'В.В. Иванов', 'А. Сидорова' ARE valid\n"
        "     person queries — extract them as-is (name='Г. Петров'). Do NOT skip abbreviated names.\n"
        "     Resolution stage will expand abbreviations. Every initial+surname combination must be\n"
        "     extracted, even if you cannot identify the full name.\n"
        "     DO NOT add generic nouns to persons: 'человек', 'мужчина', 'женщина', 'люди', 'лицо',\n"
        "     'person', 'man', 'woman', 'people' are NOT names — leave persons=[] when only\n"
        "     generic words appear (domain stays PEOPLE, attributes go to face_attributes).\n"
        "   - addresses: list of AddressQuery(value=base_address_without_corpus, query_text=full_as_written)\n"
        "   - plates (VehiclesQuerySchema): list of VehiclePlateQuery(plate=plate_number, query_text=as_written)\n"
        "3. Extract attribute filters (floors, face_attributes, car_brands, colors, object_types) if mentioned.\n"
        "4. Extract time_range if mentioned. If no time range — set null.\n"
        "   Single-day markers ('сегодня', 'today', 'за сегодня', 'сегодняшний день') MUST produce\n"
        "   since=<current_date>T00:00:00Z and until=<current_date>T23:59:59Z — never null.\n"
        "   'вчера'/'yesterday' → since=<current_date−1d>T00:00:00Z, until=<current_date−1d>T23:59:59Z.\n"
        "   Sub-day rolling windows MUST use current_datetime_utc, not calendar hour boundaries.\n"
        "   'за последний час'/'last hour' → since=(current_datetime_utc minus 1 hour),\n"
        "   until=current_datetime_utc.\n"
        "   'за последние N часов' → since=(current_datetime_utc minus N hours),\n"
        "   until=current_datetime_utc.\n"
        "   'за последние N минут' → since=(current_datetime_utc minus N minutes),\n"
        "   until=current_datetime_utc.\n"
        "   Never set time_range to null when any temporal expression is present in the query.\n"
        "   Two-digit year shorthand: 'за 25 год', 'в 24 году', 'за 24-й', '25 г.' means that year\n"
        "   in the current century. Expand: 'за 25 год' → since=2025-01-01T00:00:00Z,\n"
        "   until=2025-12-31T23:59:59Z. 'за 24 год' → since=2024-01-01T00:00:00Z,\n"
        "   until=2024-12-31T23:59:59Z.\n\n"
        "FLOOR disambiguation:\n"
        "- Extract floors ONLY when the user writes 'этаж', 'эт.', 'floor', or a bare ordinal floor number.\n"
        "- 'к<N>' or 'к<N>-<M>' in address context means корпус (building), NOT floor.\n"
        "- Do NOT extract floor numbers from корпус notation.\n\n"
        "IS_REFINEMENT detection:\n"
        "- is_refinement=True when the user adjusts/refines the SAME search (adds time, changes attribute, adds entity).\n"
        "- is_refinement=False when the user starts a completely new search (different topic, different domain).\n"
        "- Domain change (PEOPLE → VEHICLES) always means is_refinement=False.\n"
        "- If no previous context — always is_refinement=False.\n\n"
        "WHEN is_refinement=True (merge with prev_query_schema):\n"
        "- Start from prev_query_schema, apply only what the user explicitly changes.\n"
        "- Preserve all unchanged fields (entities, attributes, time_range) from previous query.\n"
        "- Example: 'А если за 2026?' → copy all from prev, change only time_range.\n"
        "- Example: 'Добавь Иванова' → copy all from prev, append new person to persons list.\n\n"
        "PRESERVE entity text:\n"
        "- query_text must be EXACTLY as the user wrote (do not correct spelling).\n"
        "  For persons: include any preceding collective quantifier in query_text.\n"
        "  'Найди всех Петровых' → query_text='всех Петровых'; "
        "'всех с фамилией Петров' → query_text='всех с фамилией Петров'.\n"
        "  The quantifier ('все', 'всех', 'каждый') is critical for entity resolution — do NOT drop it.\n"
        "- name/value/plate should be a normalized form (correct obvious errors, use canonical form).\n\n"
        + face_photo_section
        + context_section
    )
