# Service & SSE

## Нормальный поток (без interrupt)

```mermaid
flowchart TD
    REQ["POST /messages/stream"] --> AUTH["проверка владельца чата"]
    AUTH --> PREP["MinIO + face_descriptor если фото
    add_message(role=user)"]
    PREP --> RUN["app.astream_events(input, config)"]

    RUN --> STAGE["→ SSE: type=stage"]
    STAGE --> TOKEN["→ SSE: type=text (токены LLM)"]
    TOKEN --> PREV["→ SSE: type=previews"]
    PREV --> SAVE["add_message(role=assistant, type=dialog)"]
    SAVE --> DONE["→ SSE: type=done
    → SSE: data: [DONE]"]
```

---

## Поток с interrupt и resume

```mermaid
flowchart TD
    RUN["app.astream_events()"] --> INT_DET{"__interrupt__ в chunk?"}

    INT_DET -->|"нет"| RUN
    INT_DET -->|"да"| SAVE_OPT["add_message(role=assistant, type=options)"]

    SAVE_OPT --> SSE_INT["→ SSE: type=interrupt
    → SSE: data: [DONE]
    поток остановлен"]

    SSE_INT --> RESUME["POST /resolution
    {resolution_id, selected_ids}"]

    RESUME --> MARK["set_options_selected_ids()
    add_message(role=user, выбранные имена)"]

    MARK --> RUN2["app.astream_events(
    Command(resume={resolution_id, selected_ids}), config)
    граф продолжается с прерванной ноды"]

    RUN2 --> DONE["→ SSE: type=done
    → SSE: data: [DONE]"]
```

---

## SSE события — справочник

| Событие | Когда | Ключевые поля |
|---------|-------|------|
| `stage` | старт ноды | `stage: parsing\|resolution\|face_resolution\|respond` |
| `text` | токен от LLM | `content: str` |
| `interrupt` | нужен выбор | `resolution_id, entity_type, selection_mode, options` |
| `previews` | конец respond_node | `vms_link, vms_links, event_previews` |
| `done` | конец графа | `vms_link, vms_links, vms_request, event_previews` |
| `error` | timeout 300s или другая ошибка обработки | `content: str` |
| `[DONE]` | всегда в конце | sentinel |

---

## Что сохраняется в БД

| Момент | role | type | payload |
|--------|------|------|---------|
| до графа | `user` | `dialog` | `{image_key}` если фото |
| interrupt | `assistant` | `options` | `{resolution_id, entity_type, selection_mode, options}` |
| resume | `user` | `dialog` | — |
| конец графа | `assistant` | `dialog` | `{vms_link, vms_links, vms_request, event_previews}` |
