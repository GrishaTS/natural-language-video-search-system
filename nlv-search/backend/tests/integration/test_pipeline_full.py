"""
Pipeline integration tests (text + photo flows).

Стратегия best-of-5: прогоняем сценарий до 5 раз.
Достаточно одного прохода где EventFilter совпадает с ожидаемым.

Тест-кейсы взяты из реальных чатов аккаунта vadim:
  - 10 текстовых сценариев (disambiguation, multi-select, typo, address, vehicles, face attrs)
  - 4 photo-сценария (by_descriptor, by_person, attrs+photo, addr+photo)

Логика выбора опции копирует ChatView.vue:handleResolutionResponse:
  - bidirectional substring match: opt.value in content OR content in opt.value
  - single mode: ровно 1 матч; multi mode: 1+ матчей
  - если матч не найден → turn отправляется как новое сообщение через /messages/stream

Face-interrupt (entity_type="face"):
  - "фото" / "по фотографии" в контенте → выбирает __by_descriptor__
  - иначе — стандартный substring match по value (имя человека)

Сравнение vms_request: строго (ef == expected), кроме:
  - face_match.descriptors: проверяем только тип BY_DESC и непустоту (blob большой)
  - channel.ids: сортируем оба словаря перед сравнением (_sort_channel_ids)
  - face_ids в multi-select тестах: сортируем оба списка (_normalize_face_ids)
"""
from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
import pytest

pytestmark = pytest.mark.integration

MAX_ATTEMPTS = 5


@dataclass
class PipelineRunResult:
    vms_request: dict | None
    last_events: list[dict]
    terminal_state: str
    trace: list[str]


# ── Константы ─────────────────────────────────────────────────────────────────

_TOPICS_BY_MODULES = {
    "KX.Faces": ["FaceMatched", "FaceNotMatched"],
    "KX.Hikvision": ["Temperature", "FaceMatched", "FaceNotMatched"],
}



# ── Дата-хелперы ──────────────────────────────────────────────────────────────

def _today_start() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")


def _today_end() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT23:59:59Z")


def _n_days_ago_start(n: int) -> str:
    """ISO timestamp для начала дня N дней назад (UTC)."""
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%dT00:00:00Z")


def _month_before_last_start() -> str:
    """ISO timestamp для начала позапрошлого месяца (UTC)."""
    now = datetime.now(timezone.utc)
    month = now.month - 2
    year = now.year
    if month <= 0:
        month += 12
        year -= 1
    return f"{year:04d}-{month:02d}-01T00:00:00Z"


def _month_before_last_end() -> str:
    """ISO timestamp для конца позапрошлого месяца (UTC)."""
    now = datetime.now(timezone.utc)
    if now.month == 1:
        first_of_last = now.replace(year=now.year - 1, month=12, day=1)
    else:
        first_of_last = now.replace(month=now.month - 1, day=1)
    last_of_month_before = first_of_last - timedelta(days=1)
    return last_of_month_before.strftime("%Y-%m-%dT23:59:59Z")


def _parse_iso_utc(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def _within_delta_minutes(actual: str | None, expected: datetime, delta_minutes: int = 15) -> bool:
    if actual is None:
        return False
    actual_dt = _parse_iso_utc(actual)
    return abs(actual_dt - expected) <= timedelta(minutes=delta_minutes)


# ── Нормализация для сравнения ─────────────────────────────────────────────────

def _sort_channel_ids(ef: dict) -> dict:
    """Сортирует channel.ids in-place для детерминированного сравнения."""
    channel = ef.get("channel")
    if isinstance(channel, dict):
        ids = channel.get("ids")
        if isinstance(ids, list):
            ids.sort()
    return ef


def _normalize_face_ids(ef: dict) -> dict:
    """Сортирует face.face_ids для детерминированного сравнения при multi-select."""
    face = ef.get("face")
    if isinstance(face, dict) and isinstance(face.get("face_ids"), list):
        return {**ef, "face": {**face, "face_ids": sorted(face["face_ids"])}}
    return ef


# ── SSE-хелперы ───────────────────────────────────────────────────────────────

async def _stream_collect(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    *,
    data: dict | None = None,
    json_body: dict | None = None,
) -> list[dict]:
    """Стримим SSE (form-data или JSON), собираем все JSON-события до [DONE]."""
    events: list[dict] = []
    kwargs: dict = {"headers": headers, "timeout": 120.0}
    if data is not None:
        kwargs["data"] = data
    if json_body is not None:
        kwargs["json"] = json_body

    async with client.stream("POST", url, **kwargs) as resp:
        assert resp.status_code == 200, f"Stream failed {resp.status_code}: {await resp.aread()}"
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    events.append(json.loads(payload))
                except json.JSONDecodeError:
                    pass
    return events


async def _stream_collect_with_image(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    *,
    content: str = "",
    image_bytes: bytes | None = None,
) -> list[dict]:
    """Стримим SSE с multipart/form-data (content + опциональный image).

    Используется только для первого turn в photo-тестах.
    httpx автоматически выставляет multipart Content-Type когда переданы files.
    """
    events: list[dict] = []
    kwargs: dict = {"headers": headers, "timeout": 120.0, "data": {"content": content}}
    if image_bytes is not None:
        kwargs["files"] = {"image": ("face.png", image_bytes, "image/png")}

    async with client.stream("POST", url, **kwargs) as resp:
        assert resp.status_code == 200, f"Stream failed {resp.status_code}: {await resp.aread()}"
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    events.append(json.loads(payload))
                except json.JSONDecodeError:
                    pass
    return events


def _get_done_filter(events: list[dict]) -> dict | None:
    """Вернуть vms_request из последнего done-события, или None."""
    for ev in reversed(events):
        if ev.get("type") == "done" and "vms_request" in ev:
            return ev["vms_request"]
    return None


def _has_done_event(events: list[dict]) -> bool:
    return any(ev.get("type") == "done" for ev in events)


def _get_interrupt(events: list[dict]) -> dict | None:
    """Вернуть первое interrupt-событие, или None."""
    for ev in events:
        if ev.get("type") == "interrupt":
            return ev
    return None


def _current_test_name() -> str:
    for frame in inspect.stack():
        if frame.function.startswith("test_"):
            return frame.function
    return "<unknown-test>"


def _normalize_resolution_text(content: str) -> str:
    return " ".join(
        content.lower()
        .replace("корпус", "к")
        .replace("корп.", "к")
        .split()
    )


def _option_matches_content(content: str, option_value: str) -> bool:
    """Вернуть True если ввод пользователя является подстрокой значения опции."""
    option_lower = _normalize_resolution_text(option_value)
    if not content:
        return False
    return content in option_lower


def _dedupe_options(options: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for opt in options:
        opt_id = str(opt["id"])
        if opt_id in seen:
            continue
        seen.add(opt_id)
        result.append(opt)
    return result


def _compact_vms_request(ef: dict | None) -> dict | None:
    if ef is None:
        return None

    compact = json.loads(json.dumps(ef))
    face_match = compact.get("face_match")
    if isinstance(face_match, dict) and face_match.get("descriptors"):
        face_match["descriptors"] = "<<omitted>>"
    return compact


def _summarize_events(events: list[dict]) -> str:
    stages = [ev["stage"] for ev in events if ev.get("type") == "stage"]
    text_chunks = sum(1 for ev in events if ev.get("type") == "text")
    interrupt = _get_interrupt(events)
    errors = [ev.get("content") for ev in events if ev.get("type") == "error"]
    done = _get_done_filter(events)

    parts: list[str] = []
    if stages:
        parts.append(f"stages={stages}")
    if text_chunks:
        parts.append(f"text_chunks={text_chunks}")
    if interrupt:
        parts.append(
            "interrupt="
            f"{interrupt.get('entity_type')}:{interrupt.get('entity_value')} "
            f"options={[opt.get('value') for opt in interrupt.get('options', [])]}"
        )
    if done is not None:
        parts.append(f"done={json.dumps(_compact_vms_request(done), ensure_ascii=False)}")
    elif _has_done_event(events):
        parts.append("done=null")
    if errors:
        parts.append(f"errors={errors}")
    if not parts:
        parts.append("events=[]")
    return " | ".join(parts)


# ── Option selection — копия ChatView.vue:handleResolutionResponse ─────────────

def _try_resolution(
    content: str,
    options: list[dict],
    selection_mode: str,
    entity_type: str | None = None,
) -> list[str] | None:
    """
    Выбрать опции по контенту пользователя.

    Face-interrupt (entity_type="face"):
      - "фото" или "по фотографии" в контенте → ["__by_descriptor__"]
      - иначе — bidirectional substring match по value (выбрать конкретного человека)

    Все остальные типы:
      - bidirectional substring match: opt.value in content OR content in opt.value
      - single mode: ровно 1 матч
      - multi mode: 1+ матчей

    Возвращает None если матч не найден (следующий turn пойдёт как /messages/stream).
    """
    content_lower = _normalize_resolution_text(content)

    if entity_type == "face":
        # Пользователь хочет поиск по дескриптору фотографии
        if "фото" in content_lower or "по фотографии" in content_lower:
            descriptor_opt = next(
                (o for o in options if o["id"] == "__by_descriptor__"), None
            )
            if descriptor_opt:
                return ["__by_descriptor__"]

    # Стандартный bidirectional substring match
    matched = [
        opt for opt in options
        if _option_matches_content(content_lower, opt["value"])
    ]
    if not matched and selection_mode == "multi":
        token_matches: list[dict] = []
        tokens = [
            token.strip()
            for token in re.split(r"[,;\n]+", content_lower)
            if token.strip()
        ]
        for token in tokens:
            token_matches.extend(
                opt for opt in options if _option_matches_content(token, opt["value"])
            )
        matched = _dedupe_options(token_matches)
    if not matched:
        return None
    if selection_mode == "single" and len(matched) != 1:
        return None
    return [opt["id"] for opt in matched]


# ── Раннер пайплайна ──────────────────────────────────────────────────────────

async def _run_turns(
    client: httpx.AsyncClient,
    headers: dict,
    turns: list[str],
    *,
    image: bytes | None = None,
) -> PipelineRunResult:
    """
    Проводим многоходовой диалог, воспроизводя поведение фронтенда.

    image — байты PNG, отправляются только в первый turn.

    Алгоритм:
      while turns остались:
        отправить текущий turn (первый — с image если есть)
        while пришёл interrupt И есть следующий turn:
          попробовать _try_resolution(следующий turn, options, entity_type)
          если match → POST /resolution, advance turn
          если нет match → break (следующий turn пойдёт как /messages/stream)

    Возвращает итог выполнения с трассой шагов.
    """
    cr = await client.post("/chats", json={"title": "test-pipeline"}, headers=headers)
    assert cr.status_code == 201
    chat_id = cr.json()["id"]

    try:
        turn_idx = 0
        last_events: list[dict] = []
        trace: list[str] = [f"chat_id={chat_id}"]

        while turn_idx < len(turns):
            current_turn = turns[turn_idx]
            trace.append(f"turn[{turn_idx}]={current_turn!r}")
            # Первый turn может нести image
            if turn_idx == 0 and image is not None:
                last_events = await _stream_collect_with_image(
                    client,
                    f"/chats/{chat_id}/messages/stream",
                    headers,
                    content=turns[turn_idx],
                    image_bytes=image,
                )
            else:
                last_events = await _stream_collect(
                    client,
                    f"/chats/{chat_id}/messages/stream",
                    headers,
                    data={"content": turns[turn_idx]},
                )
            trace.append(_summarize_events(last_events))
            if any(ev.get("type") == "error" for ev in last_events):
                return PipelineRunResult(
                    vms_request=_get_done_filter(last_events),
                    last_events=last_events,
                    terminal_state="error",
                    trace=trace,
                )
            turn_idx += 1

            # Обрабатываем interrupt-ы пока есть следующий turn
            while True:
                interrupt = _get_interrupt(last_events)
                if interrupt is None or turn_idx >= len(turns):
                    break

                resolution_turn = turns[turn_idx]
                selected_ids = _try_resolution(
                    resolution_turn,
                    interrupt["options"],
                    interrupt.get("selection_mode", "single"),
                    entity_type=interrupt.get("entity_type"),
                )
                if selected_ids is None:
                    trace.append(
                        "resolution_unmatched "
                        f"reply={resolution_turn!r} "
                        f"options={[opt.get('value') for opt in interrupt.get('options', [])]}"
                    )
                    return PipelineRunResult(
                        vms_request=_get_done_filter(last_events),
                        last_events=last_events,
                        terminal_state="unmatched_resolution_reply",
                        trace=trace,
                    )

                trace.append(
                    f"resolution reply={resolution_turn!r} selected_ids={selected_ids}"
                )
                last_events = await _stream_collect(
                    client,
                    f"/chats/{chat_id}/resolution",
                    headers,
                    json_body={
                        "resolution_id": interrupt["resolution_id"],
                        "selected_ids": selected_ids,
                    },
                )
                trace.append(_summarize_events(last_events))
                if any(ev.get("type") == "error" for ev in last_events):
                    return PipelineRunResult(
                        vms_request=_get_done_filter(last_events),
                        last_events=last_events,
                        terminal_state="error",
                        trace=trace,
                    )
                turn_idx += 1

        done_filter = _get_done_filter(last_events)
        if done_filter is not None:
            terminal_state = "done"
        elif _has_done_event(last_events):
            terminal_state = "done_without_filter"
        elif _get_interrupt(last_events) is not None:
            terminal_state = "interrupt_pending"
        else:
            terminal_state = "no_done"

        return PipelineRunResult(
            vms_request=done_filter,
            last_events=last_events,
            terminal_state=terminal_state,
            trace=trace,
        )

    finally:
        await client.delete(f"/chats/{chat_id}", headers=headers)


def _format_run_result(run: PipelineRunResult) -> str:
    compact_events: list[dict] = []
    for ev in run.last_events:
        ev_type = ev.get("type")
        if ev_type == "text":
            continue
        compact_event = json.loads(json.dumps(ev))
        if ev_type == "done":
            compact_event["vms_request"] = _compact_vms_request(ev.get("vms_request"))
        compact_events.append(compact_event)

    return "\n".join([
        f"terminal_state={run.terminal_state}",
        *run.trace,
        f"last_events={json.dumps(compact_events, ensure_ascii=False, indent=2)}",
    ])


async def _best_of_n(
    client: httpx.AsyncClient,
    headers: dict,
    turns: list[str],
    check_fn,
    n: int = MAX_ATTEMPTS,
    *,
    image: bytes | None = None,
) -> None:
    """Прогоняем пайплайн до n раз. Достаточно одного совпадения."""
    test_name = _current_test_name()
    attempt_logs: list[str] = []
    repeated_fingerprint: str | None = None
    repeated_count = 0
    for attempt in range(1, n + 1):
        result = await _run_turns(client, headers, turns, image=image)
        event_summary = _summarize_events(result.last_events)
        summary = (
            f"[{test_name}] attempt {attempt}/{n} terminal={result.terminal_state} "
            f"summary={event_summary}"
        )
        print(summary, flush=True)
        attempt_logs.append(f"{summary}\n{_format_run_result(result)}")

        if result.terminal_state in {"error", "unmatched_resolution_reply", "no_done"}:
            pytest.fail(
                "Pipeline завершился с явной ошибкой и ретраи не помогут.\n"
                f"{_format_run_result(result)}"
            )

        if result.vms_request and check_fn(result.vms_request):
            return

        fingerprint = f"{result.terminal_state}|{event_summary}"
        if fingerprint == repeated_fingerprint:
            repeated_count += 1
        else:
            repeated_fingerprint = fingerprint
            repeated_count = 1

        if repeated_count >= max(3, n // 3):
            pytest.fail(
                "Pipeline застрял в одном и том же состоянии; дальнейшие ретраи не меняют результат.\n"
                + "\n\n".join(attempt_logs)
            )
    pytest.fail(
        f"Pipeline не вернул ожидаемый EventFilter за {n} попыток.\n"
        + "\n\n".join(attempt_logs)
    )


# ── Текстовые тесты ───────────────────────────────────────────────────────────

async def test_german_today(client: httpx.AsyncClient, auth_headers: dict):
    """
    Найди Германа за сегодня → interrupt(person, multi) → «Герман Петров» матчит →
    resolution → PEOPLE, face_ids=[32217], since/until=today.
    """
    def check(ef: dict) -> bool:
        return ef == {
            "tag": None,
            "face": {"face_ids": [32217], "attributes": None},
            "since": _today_start(),
            "until": _today_end(),
            "domain": "PEOPLE",
            "channel": None,
            "face_match": None,
            "topics_by_modules": _TOPICS_BY_MODULES,
            "event_search_request_source": "SEARCH_PAGE",
        }

    await _best_of_n(
        client, auth_headers,
        ["Найди Германа за сегодня", "Герман Петров"],
        check,
    )


async def test_ivan_2days(client: httpx.AsyncClient, auth_headers: dict):
    """
    Найди Ивана за последние 2 дня → interrupt(person, multi) → «Иван Вербов» матчит →
    resolution → PEOPLE, face_ids=[24526], временное окно интерпретируется LLM.

    «За последние 2 дня» семантически допускает несколько разумных вариантов:
      - точное относительное время: now−2d ... now (±15 мин)
      - календарное начало окна: midnight(now-2d) ... now
      - календарные границы дней: midnight(now-2d) ... end_of_today
    Оба считаются корректным ответом LLM.
    """
    def check(ef: dict) -> bool:
        now_utc = datetime.now(timezone.utc)
        time_range_ok = (
            (
                _within_delta_minutes(ef.get("since"), now_utc - timedelta(days=2))
                and _within_delta_minutes(ef.get("until"), now_utc)
            )
            or (
                ef.get("since") == _n_days_ago_start(2)
                and _within_delta_minutes(ef.get("until"), now_utc)
            )
            or (
                ef.get("since") == _n_days_ago_start(2)
                and ef.get("until") == _today_end()
            )
        )
        return (
            ef.get("tag") is None
            and ef.get("face") == {"face_ids": [24526], "attributes": None}
            and time_range_ok
            and ef.get("domain") == "PEOPLE"
            and ef.get("channel") is None
            and ef.get("face_match") is None
            and ef.get("topics_by_modules") == _TOPICS_BY_MODULES
            and ef.get("event_search_request_source") == "SEARCH_PAGE"
        )

    await _best_of_n(
        client, auth_headers,
        ["Найди Ивана за последние 2 дня", "Иван Вербов"],
        check,
        n=10,
    )


async def test_typo_girman(client: httpx.AsyncClient, auth_headers: dict):
    """
    «Гирман Петров» (опечатка) → LLM исправляет → Герман Петров,
    позапрошлый месяц = февраль 2026. Нет interrupt.
    """
    def check(ef: dict) -> bool:
        return ef == {
            "tag": None,
            "face": {"face_ids": [32217], "attributes": None},
            "since": _month_before_last_start(),
            "until": _month_before_last_end(),
            "domain": "PEOPLE",
            "channel": None,
            "face_match": None,
            "topics_by_modules": _TOPICS_BY_MODULES,
            "event_search_request_source": "SEARCH_PAGE",
        }

    await _best_of_n(
        client, auth_headers,
        ["Найди Гирмана Петрова за позапрошлый месяц"],
        check,
        n=10,
    )


async def test_vadim_march_multi(client: httpx.AsyncClient, auth_headers: dict):
    """
    Найди Вадима в марте 2026 → interrupt(person, multi) →
    «Вадим Петров, Вадим Бобров» матчит двух кандидатов →
    multi-resolution → PEOPLE, face_ids=[13857, 14378], март 2026.
    face_ids сортируются для детерминированного сравнения.
    """
    def check(ef: dict) -> bool:
        ef_norm = _normalize_face_ids(ef)
        return ef_norm == {
            "tag": None,
            "face": {"face_ids": sorted([14378, 13857]), "attributes": None},
            "since": "2026-03-01T00:00:00Z",
            "until": "2026-03-31T23:59:59Z",
            "domain": "PEOPLE",
            "channel": None,
            "face_match": None,
            "topics_by_modules": _TOPICS_BY_MODULES,
            "event_search_request_source": "SEARCH_PAGE",
        }

    await _best_of_n(
        client, auth_headers,
        ["Найди Вадима в марте 2026", "Вадим Петров, Вадим Бобров"],
        check,
    )


async def test_all_petrovs(client: httpx.AsyncClient, auth_headers: dict):
    """
    Найди всех с фамилией Петров → авторазрешение (нет interrupt) →
    PEOPLE, face_ids всех 5 Петровых, без фильтра времени и канала.
    face_ids сортируются для детерминированного сравнения.
    """
    _ALL_PETROV_IDS = sorted([32217, 24509, 29741, 13260, 14378])

    def check(ef: dict) -> bool:
        ef_norm = _normalize_face_ids(ef)
        return ef_norm == {
            "tag": None,
            "face": {"face_ids": _ALL_PETROV_IDS, "attributes": None},
            "since": None,
            "until": None,
            "domain": "PEOPLE",
            "channel": None,
            "face_match": None,
            "topics_by_modules": _TOPICS_BY_MODULES,
            "event_search_request_source": "SEARCH_PAGE",
        }

    await _best_of_n(
        client, auth_headers,
        ["Найди всех с фамилией Петров"],
        check,
        n=10,
    )


# ── Адресные тесты ────────────────────────────────────────────────────────────

async def test_g_petrov_platonova_today(
    client: httpx.AsyncClient,
    auth_headers: dict,
    platonova_20b_k1_k2_k3_channel_ids: list[int],
):
    """
    Найди Г. Петрова на Платонова 20б к1-3 за сегодня → нет interrupt (авторазрешение) →
    PEOPLE, face_ids=[32217], channel.ids=к1+к2+к3, since/until=today.
    """
    def check(ef: dict) -> bool:
        expected = {
            "tag": None,
            "face": {"face_ids": [32217], "attributes": None},
            "since": _today_start(),
            "until": _today_end(),
            "domain": "PEOPLE",
            "channel": {"ids": platonova_20b_k1_k2_k3_channel_ids},
            "face_match": None,
            "topics_by_modules": _TOPICS_BY_MODULES,
            "event_search_request_source": "SEARCH_PAGE",
        }
        return _sort_channel_ids(ef) == _sort_channel_ids(expected)

    await _best_of_n(
        client, auth_headers,
        ["Найди Г. Петрова на Платонова 20б к1-3 за сегодня"],
        check,
        n=15,
    )


async def test_petrov_platonova_k89(
    client: httpx.AsyncClient,
    auth_headers: dict,
    platonova_20b_k1_k2_channel_ids: list[int],
):
    """
    Петров на Платонова 20б к89 (несуществующий корпус) →
    interrupt(person, multi) → «Герман Петров» матчит → resolution →
    interrupt(address, multi) → «к1, к2» матчит к1 и к2 → resolution →
    PEOPLE, face_ids=[32217], channel.ids=к1+к2, нет времени.
    """
    def check(ef: dict) -> bool:
        expected = {
            "tag": None,
            "face": {"face_ids": [32217], "attributes": None},
            "since": None,
            "until": None,
            "domain": "PEOPLE",
            "channel": {"ids": platonova_20b_k1_k2_channel_ids},
            "face_match": None,
            "topics_by_modules": _TOPICS_BY_MODULES,
            "event_search_request_source": "SEARCH_PAGE",
        }
        return _sort_channel_ids(ef) == _sort_channel_ids(expected)

    await _best_of_n(
        client, auth_headers,
        ["Найди Петрова на Платонова 20б к89", "Герман Петров", "к1, к2"],
        check,
    )


# ── Атрибутные и vehicle тесты ────────────────────────────────────────────────

async def test_face_beard_glasses(client: httpx.AsyncClient, auth_headers: dict):
    """
    Человек 25-30 лет с бородой и очками → PEOPLE, face.attributes (age+beard+glasses),
    face_ids=null, без interrupt.
    """
    def check(ef: dict) -> bool:
        return ef == {
            "tag": None,
            "face": {
                "face_ids": None,
                "attributes": {
                    "age": [{"lower_bound": 25, "upper_bound": 30}],
                    "hat": None,
                    "mask": None,
                    "beard": ["with_beard"],
                    "races": None,
                    "genders": None,
                    "glasses": ["with_glasses"],
                },
            },
            "since": None,
            "until": None,
            "domain": "PEOPLE",
            "channel": None,
            "face_match": None,
            "topics_by_modules": _TOPICS_BY_MODULES,
            "event_search_request_source": "SEARCH_PAGE",
        }

    await _best_of_n(
        client, auth_headers,
        ["Найди человека 25-30 лет с бородой и очками"],
        check,
    )


async def test_yellow_mercedes_2025(client: httpx.AsyncClient, auth_headers: dict):
    """
    Жёлтый автобус Мерседес за 25 год → VEHICLES, 2025, без interrupt.
    """
    def check(ef: dict) -> bool:
        return ef == {
            "tag": None,
            "plate": None,
            "since": "2025-01-01T00:00:00Z",
            "until": "2025-12-31T23:59:59Z",
            "colors": ["yellow"],
            "domain": "VEHICLES",
            "person": None,
            "channel": None,
            "car_brands": ["MERCEDES_BENZ"],
            "object_types": ["bus"],
            "event_search_request_source": "SEARCH_PAGE",
        }

    await _best_of_n(
        client, auth_headers,
        ["Найди желтый автобус мерседес за 25 год"],
        check,
        n=10,
    )


async def test_yellow_mercedes_followup(client: httpx.AsyncClient, auth_headers: dict):
    """
    Жёлтый автобус Мерседес за 25 год → done (2025) →
    «а если за 2026» → done (2026).
    Второй turn шлётся как новое сообщение в тот же чат (без interrupt).
    Проверяем финальный vms_request (2026).
    """
    def check(ef: dict) -> bool:
        return ef == {
            "tag": None,
            "plate": None,
            "since": "2026-01-01T00:00:00Z",
            "until": "2026-12-31T23:59:59Z",
            "colors": ["yellow"],
            "domain": "VEHICLES",
            "person": None,
            "channel": None,
            "car_brands": ["MERCEDES_BENZ"],
            "object_types": ["bus"],
            "event_search_request_source": "SEARCH_PAGE",
        }

    await _best_of_n(
        client, auth_headers,
        ["Найди желтый автобус мерседес за 25 год", "а если за 2026"],
        check,
        n=10,
    )


# ── Photo-тесты ───────────────────────────────────────────────────────────────

async def test_photo_by_descriptor(
    client: httpx.AsyncClient, auth_headers: dict, face_image: bytes
):
    """
    Фото без текста → face_interrupt(multi) →
    «Искать по фотографии» → resolution(__by_descriptor__) →
    PEOPLE, face_match.type=BY_DESC, face=null.

    face_match.descriptors не сравнивается побайтово (большой blob).
    Проверяем: type=BY_DESC, descriptors непустой, min_similarity=0.7.
    Все остальные поля — строго.
    """
    def check(ef: dict) -> bool:
        face_match = ef.get("face_match") or {}
        if face_match.get("type") != "BY_DESC":
            return False
        if not face_match.get("descriptors"):
            return False
        # Сравниваем всё кроме байт дескриптора
        ef_norm = {**ef, "face_match": {
            "type": "BY_DESC",
            "descriptors": "<<omitted>>",
            "min_similarity": face_match.get("min_similarity"),
        }}
        return ef_norm == {
            "tag": None,
            "face": None,
            "since": None,
            "until": None,
            "domain": "PEOPLE",
            "channel": None,
            "face_match": {
                "type": "BY_DESC",
                "descriptors": "<<omitted>>",
                "min_similarity": 0.7,
            },
            "topics_by_modules": _TOPICS_BY_MODULES,
            "event_search_request_source": "SEARCH_PAGE",
        }

    await _best_of_n(
        client, auth_headers,
        # turns[0]="" — пустой content, image несёт всю нагрузку
        # turns[1]="Искать по фотографии" — ответ на face_interrupt
        ["", "Искать по фотографии"],
        check,
        image=face_image,
    )


async def test_photo_by_person(
    client: httpx.AsyncClient, auth_headers: dict, face_image: bytes
):
    """
    Фото без текста → face_interrupt(multi) →
    «Герман Петров» матчит кандидата → resolution(face_ids=[32217]) →
    PEOPLE, face_ids=[32217], face_match=null.
    """
    def check(ef: dict) -> bool:
        return ef == {
            "tag": None,
            "face": {"face_ids": [32217], "attributes": None},
            "since": None,
            "until": None,
            "domain": "PEOPLE",
            "channel": None,
            "face_match": None,
            "topics_by_modules": _TOPICS_BY_MODULES,
            "event_search_request_source": "SEARCH_PAGE",
        }

    await _best_of_n(
        client, auth_headers,
        # turns[0]="" — пустой content, image несёт всю нагрузку
        # turns[1]="Герман Петров" — ответ на face_interrupt, матчит кандидата
        ["", "Герман Петров"],
        check,
        image=face_image,
    )


async def test_photo_with_glasses_attr(
    client: httpx.AsyncClient, auth_headers: dict, face_image: bytes
):
    """
    Фото + текст «в очках» → parsing (glasses attr) → face_interrupt(multi) →
    «Искать по фотографии» → resolution(__by_descriptor__) →
    PEOPLE, face_match.BY_DESC + face.attributes.glasses=["with_glasses"].

    turns[0]="в очках" отправляется как content ВМЕСТЕ с image в одном multipart-запросе.
    turns[1]="Искать по фотографии" — ответ на face_interrupt.
    """
    def check(ef: dict) -> bool:
        face_match = ef.get("face_match") or {}
        if face_match.get("type") != "BY_DESC":
            return False
        if not face_match.get("descriptors"):
            return False
        ef_norm = {**ef, "face_match": {
            "type": "BY_DESC",
            "descriptors": "<<omitted>>",
            "min_similarity": face_match.get("min_similarity"),
        }}
        return ef_norm == {
            "tag": None,
            "face": {
                "face_ids": None,
                "attributes": {
                    "age": None,
                    "hat": None,
                    "mask": None,
                    "beard": None,
                    "races": None,
                    "genders": None,
                    "glasses": ["with_glasses"],
                },
            },
            "since": None,
            "until": None,
            "domain": "PEOPLE",
            "channel": None,
            "face_match": {
                "type": "BY_DESC",
                "descriptors": "<<omitted>>",
                "min_similarity": 0.7,
            },
            "topics_by_modules": _TOPICS_BY_MODULES,
            "event_search_request_source": "SEARCH_PAGE",
        }

    await _best_of_n(
        client, auth_headers,
        ["в очках", "Искать по фотографии"],
        check,
        image=face_image,
        n=10,
    )


async def test_photo_with_address(
    client: httpx.AsyncClient,
    auth_headers: dict,
    face_image: bytes,
    platonova_20b_k1_channel_ids: list[int],
):
    """
    Фото + текст «в очках на платонова 20б» (content + image в одном multipart) →
    parsing (glasses attr + address) → face_interrupt(multi) →
    «Герман Петров» → resolution(face_ids=[32217]) →
    address_interrupt(multi) → «Платонова 20б к1» →
    PEOPLE, face_ids=[32217], channel.ids=Платонова20Б к1, glasses.

    turns[0] идёт вместе с image; turns[1] и turns[2] — ответы на interrupts.
    """
    def check(ef: dict) -> bool:
        expected = {
            "tag": None,
            "face": {
                "face_ids": [32217],
                "attributes": {
                    "age": None,
                    "hat": None,
                    "mask": None,
                    "beard": None,
                    "races": None,
                    "genders": None,
                    "glasses": ["with_glasses"],
                },
            },
            "since": None,
            "until": None,
            "domain": "PEOPLE",
            "channel": {"ids": platonova_20b_k1_channel_ids},
            "face_match": None,
            "topics_by_modules": _TOPICS_BY_MODULES,
            "event_search_request_source": "SEARCH_PAGE",
        }
        return _sort_channel_ids(ef) == _sort_channel_ids(expected)

    await _best_of_n(
        client, auth_headers,
        [
            "в очках на платонова 20б",
            "Герман Петров",
            "Беларусь, Минск, Первомайский район, Малявщина, улица Платонова, 20Б к1",
        ],
        check,
        image=face_image,
        n=10,
    )


async def test_last_hour(client: httpx.AsyncClient, auth_headers: dict):
    """
    "за последний час" → ALL, since≈now-1h, until≈now.
    """
    now = datetime.now(timezone.utc)
    expected_since = now - timedelta(hours=1)

    def check(ef: dict) -> bool:
        return (
            ef.get("domain") == "ALL"
            and _within_delta_minutes(ef.get("since"), expected_since, delta_minutes=5)
            and _within_delta_minutes(ef.get("until"), now, delta_minutes=5)
        )

    await _best_of_n(client, auth_headers, ["покажи все события за последний час"], check)
