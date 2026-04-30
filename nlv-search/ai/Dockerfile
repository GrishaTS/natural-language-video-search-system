FROM python:3.11-slim

ARG INSTALL_DEV=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src \
    APP_MODULE=main:app \
    AI_PORT=8501 \
    AI_WORKERS=1 \
    AI_LOG_LEVEL=info \
    AI_RELOAD=false

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./pyproject.toml
RUN pip install --upgrade pip \
&& if [ "$INSTALL_DEV" = "true" ]; then pip install ".[dev]"; else pip install .; fi

COPY src ./src
COPY tests ./tests

EXPOSE 8501

CMD ["sh", "-c", "UVICORN_CMD=\"uvicorn ${APP_MODULE} --host 0.0.0.0 --port ${AI_PORT} --log-level ${AI_LOG_LEVEL}\"; if [ \"$AI_RELOAD\" = \"true\" ]; then UVICORN_CMD=\"$UVICORN_CMD --reload\"; else UVICORN_CMD=\"$UVICORN_CMD --workers ${AI_WORKERS}\"; fi; exec $UVICORN_CMD"]
