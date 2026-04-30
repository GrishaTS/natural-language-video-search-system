# Natural Language Video Search — AI Service

<img width="1626" height="1218" alt="telegram-cloud-photo-size-2-5442902666158741514-w" src="https://github.com/user-attachments/assets/28256815-9231-4166-9815-32f135f5eea8" />

___
## About
*Natural Language Video Search — AI Service is a lightweight FastAPI microservice that provides a unified access point to LLM inference and text embeddings for the backend. It abstracts provider differences behind a single API and protects all endpoints with a shared Bearer token.*

Key features:
- Text embedding generation via TEI (Text Embeddings Inference)
- Chat completion proxy supporting vLLM (self-hosted, OpenAI-compatible) and OpenRouter (cloud)
- Runtime provider switching via the `LLM_PROVIDER` environment variable
- Bearer token authentication for all endpoints

___
## Project Structure

<details open>
  <summary>📂 ai/</summary>
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

___
## Technologies Used
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi) ![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-333333?logo=uvicorn) ![Pydantic](https://img.shields.io/badge/Pydantic-Validation-4B8BBE?logo=pydantic) ![HTTPX](https://img.shields.io/badge/HTTP-Client-0E8AC8) ![TEI](https://img.shields.io/badge/Embeddings-TEI-FF6B6B) ![vLLM](https://img.shields.io/badge/Inference-vLLM-412991) ![OpenRouter](https://img.shields.io/badge/LLM-OpenRouter-6366F1)
