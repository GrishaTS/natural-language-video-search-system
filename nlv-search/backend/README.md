# Natural Language Video Search — Backend

<img width="1340" height="1858" alt="telegram-cloud-photo-size-2-5442902666158741517-w" src="https://github.com/user-attachments/assets/d1232121-ee0b-4338-ac32-e4ea9c242528" />

___
## About
*Natural Language Video Search — Backend is the server-side component of the system, built with FastAPI. It orchestrates a LangGraph conversational agent that translates natural language queries into structured VMS API requests and streams results back to the client via SSE.*

Key features:
- Conversational search agent powered by LangGraph with multi-turn memory (PostgreSQL checkpointer)
- Parallel entity resolution: persons, vehicles, and addresses via Qdrant vector search
- Face-based search: descriptor matching or registry lookup with user-driven disambiguation
- SSE streaming of agent stages, LLM tokens, interrupt events, and search previews
- JWT authentication with Redis-backed token blacklist
- Photo upload to MinIO with on-demand presigned URL generation
- Background VMS → Qdrant entity sync via `entities_populator`

___
## Project Structure

<details open>
  <summary>📂 backend/</summary>
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

___
## Technologies Used
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi) ![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-333333?logo=uvicorn) ![Pydantic](https://img.shields.io/badge/Pydantic-Validation-4B8BBE?logo=pydantic) ![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy-000000?logo=sqlalchemy) ![Asyncpg](https://img.shields.io/badge/PostgreSQL-Asyncpg-00599C) ![LangGraph](https://img.shields.io/badge/Agent-LangGraph-1C3C3C?logo=langchain) ![LangChain](https://img.shields.io/badge/LLM-LangChain-1C3C3C?logo=langchain) ![Redis](https://img.shields.io/badge/Cache-Redis-DC382D?logo=redis) ![MinIO](https://img.shields.io/badge/ObjectStorage-MinIO-F05032?logo=minio) ![Qdrant](https://img.shields.io/badge/VectorDB-Qdrant-FF6F00) ![HTTPX](https://img.shields.io/badge/HTTP-Client-0E8AC8) ![PyJWT](https://img.shields.io/badge/Auth-PyJWT-000000) ![Python--Multipart](https://img.shields.io/badge/Uploads-Multipart-FFD43B)
