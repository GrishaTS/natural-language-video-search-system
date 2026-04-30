# Фото-трек

## До графа (service.py)

```mermaid
flowchart TD
    REQ["POST /messages/stream
    multipart: content + image"]

    REQ --> HAS{"image?"}

    HAS -->|"нет"| GRAPH
    HAS -->|"да"| MINIO["MinIO.upload_chat_image()
    → image_key → message.payload"]

    MINIO --> DESC["VmsAPI.get_face_descriptor()
    → face_descriptor"]

    DESC --> GRAPH["graph input:
    messages, face_descriptor"]
```

---

## face_prep_node (text + photo)

```mermaid
flowchart LR
    IN["query_schema.persons = ['Иванов']
    face_descriptor = {...}"]

    IN --> PREP["face_prep_node
    query_schema.persons ← []"]

    PREP --> OUT["persons не пойдут в entity_resolution
    человека ищем по лицу, не по имени"]
```

---

## face_resolution

```mermaid
flowchart TD
    DESC["face_descriptor из state"]
    DESC --> SEARCH["face_resolution_search_node
    VmsAPI.search_faces_by_descriptor()
    → face_candidates"]

    SEARCH --> INT["⏸ face_resolution_apply_node — interrupt
    options: кандидаты + 'Искать по фотографии'
    selection_mode: multi"]

    INT -->|"Command(resume=selected_ids)"| CHOOSE{"выбор"}

    CHOOSE -->|"персоны из реестра"| IDS["FaceResolution
    mode=by_ids
    face_ids=[...]
    person_names=[...]"]

    CHOOSE -->|"'Искать по фотографии'"| DESC2["FaceResolution
    mode=by_descriptor
    descriptor=face_descriptor"]

    IDS & DESC2 --> STATE["face_resolution → state
    (живёт между турнами)"]
```

> Выбор одновременно персон и "Искать по фотографии" — ошибка 400.

---

## face_resolution → EventFilter

```mermaid
flowchart LR
    FR{"face_resolution.mode"}

    FR -->|"by_ids"| FID["FaceFilter
    face_ids=[id1, id2]"]

    FR -->|"by_descriptor"| FDM["FaceMatchFilter
    type=BY_DESC
    descriptors=[[descriptor]]
    min_similarity=0.7"]

    FID & FDM --> EF["PersonEventFilter"]

    FA["face_attributes из текста
    (пол, возраст, очки...)"] --> EF
```

`face_resolution` приоритетнее `selected_entities` для персон.

---

## Жизненный цикл image_key

```mermaid
flowchart LR
    UP["upload → image_key"] --> DB["message.payload.image_key
    (PostgreSQL)"]

    DB -->|"GET /chats/{id}"| URL["proxy URL: /api/v1/media/chat-image/{key}
    (auth check + MinIO read)"]

    DB -->|"DELETE /chats/{id}"| DEL["get_image_keys()
    → MinIO.delete_images()"]
```
