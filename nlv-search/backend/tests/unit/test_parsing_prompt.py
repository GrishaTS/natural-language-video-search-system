from src.prompts.conversational_search.parsing import get_parsing_system_prompt


def test_parsing_prompt_includes_current_datetime_for_subday_windows() -> None:
    prompt = get_parsing_system_prompt(
        prev_query_schema=None,
        prev_selected_entities=None,
        prev_latest_summary=None,
        current_date="2026-04-18",
        current_datetime_utc="2026-04-18T01:23:45Z",
    )

    assert "Current datetime UTC: 2026-04-18T01:23:45Z." in prompt
    assert "Sub-day rolling windows MUST use current_datetime_utc" in prompt
    assert "'за последний час'/'last hour' → since=(current_datetime_utc minus 1 hour)," in prompt
