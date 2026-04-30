def get_respond_system_prompt() -> str:
    """Build the system prompt for the respond LLM node."""

    return (
        "Task: Write a concise Russian-language narrative answer about the search results.\n"
        "You receive: event summary statistics, a vms_link to VMS UI, and the resolved entities.\n\n"
        "ANSWER STYLE:\n"
        "- Plain narrative, 5-7 sentences. No bullet lists, no bold headers.\n"
        "- Lead with the main fact: subject (person / plate / address), total event count, time span.\n"
        "- Then add location context: address, floor/zone if relevant.\n"
        "- If multiple cameras/locations: mention count and most frequent one, not exhaustive list.\n"
        "- If zero events: one sentence saying nothing was found, suggest refining the query.\n\n"
        "ALWAYS OMIT:\n"
        "- Internal IDs, similarity scores, list names.\n"
        "- Race/nationality breakdown.\n"
        "- Per-attribute zero counts.\n"
        "- Attribute statistics when the search was for a specific named person or plate.\n\n"
        "End with a sentence inviting the user to refine the query or follow the vms_link if events were found.\n"
        "Stop immediately after the final sentence. No trailing text.\n"
    )
