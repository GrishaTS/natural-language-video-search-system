FROM python:3.11-slim

ARG INSTALL_DEV=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src \
    APP_MODULE=main:app \
    BACKEND_PORT=8000 \
    BACKEND_WORKERS=1 \
    BACKEND_LOG_LEVEL=info \
    BACKEND_RELOAD=false

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY pyproject.toml ./pyproject.toml
RUN pip install --upgrade pip \
    && if [ "$INSTALL_DEV" = "true" ]; then pip install ".[dev]"; else pip install .; fi

COPY src ./src
COPY tests ./tests

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "UVICORN_CMD=\"uvicorn ${APP_MODULE} --host 0.0.0.0 --port ${BACKEND_PORT} --log-level ${BACKEND_LOG_LEVEL}\"; if [ \"$BACKEND_RELOAD\" = \"true\" ]; then UVICORN_CMD=\"$UVICORN_CMD --reload\"; else UVICORN_CMD=\"$UVICORN_CMD --workers ${BACKEND_WORKERS}\"; fi; exec $UVICORN_CMD"]
