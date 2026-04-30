# Natural Language Video Search

___
## About
*Natural Language Video Search is a conversational search system over a video archive that integrates:*
- A FastAPI backend orchestrating a LangGraph agent with multi-turn conversational memory
- An AI microservice proxying TEI (text embeddings) and vLLM / OpenRouter (LLM inference)
- Integration with a VMS (Video Management System) API as the source of video analytics events
- PostgreSQL, Redis, Qdrant, and MinIO as the data layer
- Fully containerized with Docker Compose; secrets managed via SOPS + age

> **Note:** This is a public version of a commercial outsource project. The VMS (Video Management System) API and infrastructure credentials are not included, so the system cannot be run as-is.

___
## Architecture
```
Frontend (Vue 3 / Vite  :3000)
 └─► Backend (FastAPI    :8000)
      ├─► PostgreSQL :5432   — chats, messages, users
      ├─► Redis      :6379   — cache, JWT blacklist
      ├─► Qdrant     :6333   — entity vector search
      ├─► MinIO      :9000   — photo storage
      ├─► AI Service :8501
      │       ├─► TEI        — text embeddings (multilingual-e5-base)
      │       └─► vLLM       — LLM inference (OpenAI-compatible)
      └─► VMS API            — external video analytics events API
```
Detailed diagrams — [`diagrams/`](diagrams/).

___
## Project Structure

<details open>
  <summary>📂 natural-language-video-search-system</summary>

  <ul>
    <li>📄 <code>docker-compose.yml</code> — Docker services configuration</li>
    <li>📄 <code>Makefile</code> — Shortcuts for common operations (env / up / down / test)</li>
    <li>📄 <code>.env.example</code> — Environment variables template</li>
    <li>📄 <code>.env.sops</code> — Encrypted environment variables (SOPS + age)</li>
    <li>📄 <code>.sops.yaml</code> — SOPS encryption configuration</li>
  </ul>

  <ul>

  <details open>
    <summary>📂 nlv-search/ — Application services (backend, frontend, ai)</summary>
    <ul>

  <details>
    <summary>📂 <a href="https://github.com/GrishaTS/natural-language-video-search-system/tree/main/nlv-search/backend" target="_blank">backend/</a> — FastAPI backend (LangGraph agent + integrations)</summary>
    <ul>
      <li>📄 <code>.dockerignore</code> — Files and folders excluded from Docker build context</li>
      <li>📄 <code>Dockerfile</code> — Instructions for building the backend Docker image</li>
      <li>📄 <code>pyproject.toml</code> — Python dependencies and project metadata</li>
      <details>
        <summary>📂 src/</summary>
        <ul>
          <li>📄 <code>main.py</code> — FastAPI application entry point</li>
          <details>
            <summary>📂 api/</summary>
            <ul>
              <li>📄 <code>router.py</code> — Root API router combining all sub-routers</li>
              <details>
                <summary>📂 auth/</summary>
                <ul>
                  <li>📄 <code>router.py</code> — Registration, login, logout, token refresh endpoints</li>
                  <li>📄 <code>schemas.py</code> — Auth request and response Pydantic models</li>
                  <li>📄 <code>deps.py</code> — Auth dependency (current user extraction)</li>
                </ul>
              </details>
              <details>
                <summary>📂 conversational_search/</summary>
                <ul>
                  <li>📄 <code>router.py</code> — Chats CRUD, messages/stream SSE, resolution endpoints</li>
                  <li>📄 <code>schemas.py</code> — Chat, message, and resolution request/response models</li>
                </ul>
              </details>
              <details>
                <summary>📂 health/</summary>
                <ul>
                  <li>📄 <code>router.py</code> — Health and dependency status endpoints</li>
                  <li>📄 <code>schemas.py</code> — Health response models</li>
                </ul>
              </details>
              <details>
                <summary>📂 media/</summary>
                <ul>
                  <li>📄 <code>router.py</code> — Presigned URL proxy endpoint</li>
                </ul>
              </details>
            </ul>
          </details>
          <details>
            <summary>📂 core/</summary>
            <ul>
              <li>📄 <code>config.py</code> — Application settings via Pydantic Settings</li>
              <li>📄 <code>security.py</code> — JWT creation and validation</li>
              <li>📄 <code>auth.py</code> — Auth dependency helpers</li>
              <li>📄 <code>logger.py</code> — Structured logging setup</li>
            </ul>
          </details>
          <details>
            <summary>📂 domain/</summary>
            <ul>
              <li>📄 <code>entity.py</code> — ResolvedEntity and related models</li>
              <li>📄 <code>attributes.py</code> — Face and vehicle attribute types</li>
              <li>📄 <code>entity_naming.py</code> — Entity display name helpers</li>
              <li>📄 <code>enums.py</code> — Domain enumerations</li>
            </ul>
          </details>
          <details>
            <summary>📂 infra/</summary>
            <ul>
              <details>
                <summary>📂 ai/</summary>
                <ul>
                  <li>📄 <code>client.py</code> — HTTPX client for the AI service</li>
                  <details>
                    <summary>📂 embed/</summary>
                    <ul>
                      <li>📄 <code>api.py</code> — Text embedding request method</li>
                      <li>📄 <code>schemas.py</code> — Embed request/response models</li>
                    </ul>
                  </details>
                  <details>
                    <summary>📂 llm/</summary>
                    <ul>
                      <li>📄 <code>api.py</code> — Chat completion request method</li>
                      <li>📄 <code>schemas.py</code> — LLM request/response models</li>
                    </ul>
                  </details>
                  <details>
                    <summary>📂 health/</summary>
                    <ul>
                      <li>📄 <code>api.py</code> — AI service health check method</li>
                      <li>📄 <code>schemas.py</code> — Health response models</li>
                    </ul>
                  </details>
                  <details>
                    <summary>📂 langchain/</summary>
                    <ul>
                      <li>📄 <code>llm.py</code> — LangChain-compatible LLM adapter</li>
                    </ul>
                  </details>
                </ul>
              </details>
              <details>
                <summary>📂 minio/</summary>
                <ul>
                  <li>📄 <code>database.py</code> — MinIO client setup</li>
                  <details>
                    <summary>📂 conversational_search/</summary>
                    <ul>
                      <li>📄 <code>repository.py</code> — Chat image upload, presigned URL, and delete</li>
                    </ul>
                  </details>
                </ul>
              </details>
              <details>
                <summary>📂 postgres/</summary>
                <ul>
                  <li>📄 <code>database.py</code> — Async SQLAlchemy engine and session factory</li>
                  <details>
                    <summary>📂 auth/</summary>
                    <ul>
                      <li>📄 <code>models.py</code> — User SQLAlchemy model</li>
                      <li>📄 <code>repository.py</code> — User CRUD operations</li>
                    </ul>
                  </details>
                  <details>
                    <summary>📂 conversational_search/</summary>
                    <ul>
                      <li>📄 <code>models.py</code> — Chat and Message SQLAlchemy models</li>
                      <li>📄 <code>repository.py</code> — Chat and message CRUD operations</li>
                    </ul>
                  </details>
                  <details>
                    <summary>📂 langgraph/</summary>
                    <ul>
                      <li>📄 <code>checkpointer.py</code> — PostgreSQL checkpointer for LangGraph state persistence</li>
                    </ul>
                  </details>
                </ul>
              </details>
              <details>
                <summary>📂 qdrant/</summary>
                <ul>
                  <li>📄 <code>database.py</code> — Qdrant async client setup</li>
                  <details>
                    <summary>📂 conversational_search/</summary>
                    <ul>
                      <li>📄 <code>repository.py</code> — People, vehicle, and address vector search</li>
                    </ul>
                  </details>
                </ul>
              </details>
              <details>
                <summary>📂 redis/</summary>
                <ul>
                  <li>📄 <code>database.py</code> — Redis async client setup</li>
                  <li>📄 <code>auth_blacklist.py</code> — JWT blacklist add and check operations</li>
                </ul>
              </details>
              <details>
                <summary>📂 vms/</summary>
                <ul>
                  <li>📄 <code>client.py</code> — HTTPX client for the VMS API</li>
                  <li>📄 <code>api.py</code> — VMS API methods (events, faces, channels, tags)</li>
                  <li>📄 <code>schemas.py</code> — VMS response Pydantic models</li>
                  <li>📄 <code>mappers.py</code> — VMS response → domain model converters</li>
                </ul>
              </details>
            </ul>
          </details>
          <details>
            <summary>📂 prompts/</summary>
            <ul>
              <details>
                <summary>📂 conversational_search/</summary>
                <ul>
                  <li>📄 <code>parsing.py</code> — System prompt for the parsing node</li>
                  <li>📄 <code>resolution.py</code> — System prompt for the entity resolution node</li>
                  <li>📄 <code>respond.py</code> — System prompt for the respond node</li>
                </ul>
              </details>
            </ul>
          </details>
          <details>
            <summary>📂 services/</summary>
            <ul>
              <details>
                <summary>📂 auth/</summary>
                <ul>
                  <li>📄 <code>service.py</code> — User registration and authentication logic</li>
                </ul>
              </details>
              <details>
                <summary>📂 conversational_search/</summary>
                <ul>
                  <li>📄 <code>graph.py</code> — LangGraph StateGraph definition and routing</li>
                  <li>📄 <code>service.py</code> — SSE orchestration and interrupt/resume logic</li>
                  <li>📄 <code>state.py</code> — ConversationState TypedDict</li>
                  <li>📄 <code>utils.py</code> — Graph utility helpers</li>
                  <details>
                    <summary>📂 nodes/</summary>
                    <ul>
                      <li>📄 <code>parsing.py</code> — LLM-based query parsing node</li>
                      <li>📄 <code>resolution.py</code> — Entity resolution search and apply nodes</li>
                      <li>📄 <code>face_resolution.py</code> — Face prep, search, and apply nodes</li>
                      <li>📄 <code>respond.py</code> — VMS search and LLM narrative generation node</li>
                    </ul>
                  </details>
                  <details>
                    <summary>📂 schemas/</summary>
                    <ul>
                      <li>📄 <code>query.py</code> — PeopleQuerySchema, VehiclesQuerySchema, AllQuerySchema</li>
                      <li>📄 <code>resolution.py</code> — AutoResolve, UserResolve, ResolutionOutput</li>
                    </ul>
                  </details>
                  <details>
                    <summary>📂 usecases/</summary>
                    <ul>
                      <li>📄 <code>event_filter_builder.py</code> — Builds VMS EventFilter from conversation state</li>
                      <li>📄 <code>event_summarizer.py</code> — Structures VMS events into typed summaries for the LLM</li>
                      <li>📄 <code>summary_schemas.py</code> — PeopleSummary, VehicleSummary, AllSummary models</li>
                      <li>📄 <code>vms_search.py</code> — VMS event search, channel and tag resolution</li>
                      <li>📄 <code>vms_link_builder.py</code> — Generates single and per-person VMS deep-link URLs</li>
                    </ul>
                  </details>
                </ul>
              </details>
              <details>
                <summary>📂 entities_populator/</summary>
                <ul>
                  <li>📄 <code>service.py</code> — Background VMS → Qdrant entity sync orchestration</li>
                  <li>📄 <code>collections.py</code> — Qdrant collection definitions</li>
                  <li>📄 <code>qdrant_upsert.py</code> — Entity embedding and upsert logic</li>
                </ul>
              </details>
            </ul>
          </details>
        </ul>
      </details>
      <li>📂 tests/ — pytest unit &amp; integration tests</li>
    </ul>
  </details>

  <details>
    <summary>📂 <a href="https://github.com/GrishaTS/natural-language-video-search-system/tree/main/nlv-search/ai" target="_blank">ai/</a> — FastAPI AI microservice (TEI &amp; vLLM proxy)</summary>
    <ul>
      <li>📄 <code>.dockerignore</code> — Files and folders excluded from Docker build context</li>
      <li>📄 <code>Dockerfile</code> — Instructions for building the AI service Docker image</li>
      <li>📄 <code>pyproject.toml</code> — Python dependencies and project metadata</li>
      <details>
        <summary>📂 src/</summary>
        <ul>
          <li>📄 <code>main.py</code> — FastAPI application entry point</li>
          <details>
            <summary>📂 api/</summary>
            <ul>
              <li>📄 <code>router.py</code> — Root API router combining all sub-routers</li>
              <details>
                <summary>📂 auth/</summary>
                <ul>
                  <li>📄 <code>deps.py</code> — Bearer token validation dependency</li>
                </ul>
              </details>
              <details>
                <summary>📂 embed/</summary>
                <ul>
                  <li>📄 <code>router.py</code> — POST /embed/text — text embedding endpoint</li>
                </ul>
              </details>
              <details>
                <summary>📂 llm/</summary>
                <ul>
                  <li>📄 <code>router.py</code> — POST /chat/completions — chat completion proxy endpoint</li>
                </ul>
              </details>
              <details>
                <summary>📂 health/</summary>
                <ul>
                  <li>📄 <code>router.py</code> — GET /health, GET /health/services endpoints</li>
                  <li>📄 <code>schemas.py</code> — Health response models</li>
                </ul>
              </details>
            </ul>
          </details>
          <details>
            <summary>📂 core/</summary>
            <ul>
              <li>📄 <code>config.py</code> — LLM provider and service settings</li>
              <li>📄 <code>security.py</code> — Bearer token check</li>
              <li>📄 <code>logger.py</code> — Structured logging setup</li>
            </ul>
          </details>
          <details>
            <summary>📂 infra/</summary>
            <ul>
              <details>
                <summary>📂 tei/</summary>
                <ul>
                  <li>📄 <code>client.py</code> — HTTPX client for TEI</li>
                  <li>📄 <code>api.py</code> — Embedding request method</li>
                  <li>📄 <code>schemas.py</code> — TEI request/response models</li>
                </ul>
              </details>
              <details>
                <summary>📂 vllm/</summary>
                <ul>
                  <li>📄 <code>client.py</code> — HTTPX client for vLLM</li>
                  <li>📄 <code>api.py</code> — Chat completion request method</li>
                  <li>📄 <code>schemas.py</code> — vLLM request/response models</li>
                </ul>
              </details>
              <details>
                <summary>📂 openrouter/</summary>
                <ul>
                  <li>📄 <code>client.py</code> — HTTPX client for OpenRouter</li>
                  <li>📄 <code>api.py</code> — Chat completion request method</li>
                </ul>
              </details>
            </ul>
          </details>
        </ul>
      </details>
      <li>📂 tests/ — pytest tests</li>
    </ul>
  </details>

  <details>
    <summary>📂 <a href="https://github.com/GrishaTS/natural-language-video-search-system/tree/main/nlv-search/frontend" target="_blank">frontend/</a> — Vue 3 + TypeScript SPA</summary>
    <ul>
      <li>📄 <code>.dockerignore</code> — Files and folders excluded from Docker build context</li>
      <li>📄 <code>Dockerfile</code> — Instructions for building the frontend Docker image</li>
      <li>📄 <code>package.json</code> — Node.js dependencies and scripts</li>
      <li>📄 <code>vite.config.ts</code> — Vite build configuration</li>
      <li>📄 <code>tsconfig.json</code> — TypeScript configuration</li>
      <li>📄 <code>index.html</code> — HTML entry point</li>
      <details>
        <summary>📂 src/</summary>
        <ul>
          <li>📄 <code>main.ts</code> — Application entry point</li>
          <li>📄 <code>App.vue</code> — Root component</li>
          <details>
            <summary>📂 api/</summary>
            <ul>
              <li>📄 <code>auth.ts</code> — Auth API calls (login, register, refresh)</li>
              <li>📄 <code>conversationalSearch.ts</code> — Chat and SSE streaming API calls</li>
              <li>📄 <code>health.ts</code> — Services health API calls</li>
              <li>📄 <code>http.ts</code> — Axios instance with interceptors</li>
              <li>📄 <code>errors.ts</code> — API error types</li>
            </ul>
          </details>
          <details>
            <summary>📂 components/</summary>
            <ul>
              <li>📄 <code>AppAlert.vue</code> — Global alert component</li>
              <li>📄 <code>AppHero.vue</code> — Landing hero section</li>
              <li>📄 <code>PromptExamples.vue</code> — Sample query suggestions</li>
              <details>
                <summary>📂 chat/</summary>
                <ul>
                  <li>📄 <code>ChatMessages.vue</code> — Message list renderer</li>
                  <li>📄 <code>SearchResultMessageCard.vue</code> — Result card with previews and VMS links</li>
                  <li>📄 <code>InlineOptionsMessageCard.vue</code> — Entity disambiguation selection card</li>
                  <li>📄 <code>vmsLinks.ts</code> — VMS deep-link formatting utilities</li>
                </ul>
              </details>
              <details>
                <summary>📂 status/</summary>
                <ul>
                  <li>📄 <code>ServicesStatusGrid.vue</code> — External services health status grid</li>
                </ul>
              </details>
            </ul>
          </details>
          <details>
            <summary>📂 composables/</summary>
            <ul>
              <li>📄 <code>useAuthGuard.ts</code> — Route authentication guard</li>
              <li>📄 <code>useMarkdownRenderer.ts</code> — Markdown-to-HTML rendering</li>
              <li>📄 <code>useSamplePrompts.ts</code> — Sample prompt rotation logic</li>
            </ul>
          </details>
          <details>
            <summary>📂 stores/</summary>
            <ul>
              <li>📄 <code>auth.ts</code> — Auth state (user, tokens, login/logout)</li>
              <li>📄 <code>chat.ts</code> — Chat and message state with SSE handling</li>
            </ul>
          </details>
          <details>
            <summary>📂 types/</summary>
            <ul>
              <li>📄 <code>auth.ts</code> — Auth request/response types</li>
              <li>📄 <code>chat.ts</code> — Chat, message, and SSE event types</li>
              <li>📄 <code>health.ts</code> — Health status types</li>
              <li>📄 <code>common.ts</code> — Shared utility types</li>
            </ul>
          </details>
          <details>
            <summary>📂 views/</summary>
            <ul>
              <li>📄 <code>AuthView.vue</code> — Login and registration page</li>
              <li>📄 <code>ChatViewLanggraph.vue</code> — Main conversational search page</li>
              <li>📄 <code>ProfileView.vue</code> — User profile page</li>
              <li>📄 <code>StatusView.vue</code> — External services status page</li>
            </ul>
          </details>
          <li>📄 <code>router/index.ts</code> — Vue Router route definitions</li>
          <li>📄 <code>config/index.ts</code> — Application configuration constants</li>
        </ul>
      </details>
    </ul>
  </details>

  </details>

  <details>
    <summary>📂 <a href="https://github.com/GrishaTS/natural-language-video-search-system/tree/main/notebooks" target="_blank">notebooks/</a> — Research (QVHighlights benchmark, retrieval models)</summary>
    <ul>
      <li>📄 README.md — results table &amp; methodology</li>
      <li>📄 config.py — paths, model names, hyperparameters</li>
      <li>📄 requirements.txt</li>
      <li>📄 clearml.yml</li>
      <li>📄 00_dataset.ipynb — QVHighlights download &amp; EDA</li>
      <li>📄 01 qwen3.ipynb — Qwen3-VL-Embedding pipeline</li>
      <li>📄 02 clip.ipynb — CLIP ViT-L/14 pipeline</li>
      <li>📄 03 xclip.ipynb — X-CLIP pipeline</li>
      <li>📄 04 momentdetr_direct.ipynb — CG-DETR direct grounding</li>
      <li>📄 05 momentdetr_cross.ipynb — CG-DETR cross-encoder saliency</li>
      <details>
        <summary>📂 utils/</summary>
        <ul>
          <li>📄 download.py — dataset &amp; annotations</li>
          <li>📄 frames.py — video frame extraction</li>
          <li>📄 clip_embedder.py — CLIP / X-CLIP wrappers</li>
          <li>📄 qwen_embedder.py — Qwen3-VL-Embedding wrapper</li>
          <li>📄 reranker.py — Qwen3-VL-Reranker wrapper</li>
          <li>📄 indexing.py — FAISS index build &amp; persist</li>
          <li>📄 search.py — candidate retrieval &amp; segment merging</li>
          <li>📄 metrics.py — mAP, R1@0.5, R1@0.7, IoU</li>
          <li>📄 clearml_logger.py — experiment logging</li>
        </ul>
      </details>
    </ul>
  </details>

  </ul>

</details>

___
## Technologies Used
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi) ![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-333333?logo=uvicorn) ![Pydantic](https://img.shields.io/badge/Pydantic-Validation-4B8BBE?logo=pydantic) ![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy-000000?logo=sqlalchemy) ![Asyncpg](https://img.shields.io/badge/PostgreSQL-Asyncpg-00599C) ![LangGraph](https://img.shields.io/badge/Agent-LangGraph-1C3C3C?logo=langchain) ![LangChain](https://img.shields.io/badge/LLM-LangChain-1C3C3C?logo=langchain) ![Redis](https://img.shields.io/badge/Cache-Redis-DC382D?logo=redis) ![MinIO](https://img.shields.io/badge/ObjectStorage-MinIO-F05032?logo=minio) ![Qdrant](https://img.shields.io/badge/VectorDB-Qdrant-FF6F00) ![HTTPX](https://img.shields.io/badge/HTTP-Client-0E8AC8) ![PyJWT](https://img.shields.io/badge/Auth-PyJWT-000000) ![Python--Multipart](https://img.shields.io/badge/Uploads-Multipart-FFD43B) ![Vue 3](https://img.shields.io/badge/UI-Vue_3-4FC08D?logo=vue.js) ![TypeScript](https://img.shields.io/badge/Language-TypeScript-3178C6?logo=typescript) ![Vite](https://img.shields.io/badge/Build-Vite-646CFF?logo=vite) ![Pinia](https://img.shields.io/badge/State-Pinia-FFD859) ![Axios](https://img.shields.io/badge/HTTP-Axios-5A29E4) ![TEI](https://img.shields.io/badge/Embeddings-TEI-FF6B6B) ![vLLM](https://img.shields.io/badge/Inference-vLLM-412991) ![OpenRouter](https://img.shields.io/badge/LLM-OpenRouter-6366F1) ![Docker](https://img.shields.io/badge/Container-Docker-2496ED?logo=docker) ![SOPS](https://img.shields.io/badge/Secrets-SOPS-FF9900) ![age](https://img.shields.io/badge/Encryption-age-333333)

___
**Author**: Bezrukov Grigoriy
- **Mail**: `bezgrisa@gmail.com`
- **Telegram**: [@bezGriga](https://t.me/bezGriga)

**Project Supervisor:**  Akhmetov Vadim