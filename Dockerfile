FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MUSIC_REVIEW_PROJECT_ROOT=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts

RUN python -m pip install --upgrade pip \
    && python -m pip install .

COPY assets ./assets
COPY deploy/docker-entrypoint-api.sh /usr/local/bin/docker-entrypoint-api.sh

RUN mkdir -p /app/data \
    && chmod +x /usr/local/bin/docker-entrypoint-api.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl --fail http://127.0.0.1:8000/health || exit 1

CMD ["/usr/local/bin/docker-entrypoint-api.sh"]
