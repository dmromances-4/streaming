FROM python:3.12-slim-bookworm

WORKDIR /app

COPY shared/python /app/shared/python
COPY catalog/data/seed /app/catalog/data/seed
COPY catalog/data/cocktails /app/catalog/data/cocktails
COPY catalog/data/media-aliases.yaml /app/catalog/data/media-aliases.yaml
COPY skills/catalog-metadata/pyproject.toml /app/skills/catalog-metadata/
COPY skills/catalog-metadata/src /app/skills/catalog-metadata/src

WORKDIR /app/skills/catalog-metadata

RUN pip install --no-cache-dir \
    fastapi>=0.115.0 \
    "uvicorn[standard]>=0.32.0" \
    httpx>=0.27.0 \
    structlog>=24.4.0 \
    prometheus-client>=0.21.0 \
    pydantic>=2.9.0 \
    pydantic-settings>=2.6.0 \
    pyyaml>=6.0.0 \
    aiosqlite>=0.20.0

ENV PYTHONPATH=/app/skills/catalog-metadata/src:/app/shared/python
ENV DATABASE_PATH=/data/catalog.db
ENV SEED_DIR=/app/catalog/data/seed
ENV COCKTAILS_DIR=/app/catalog/data/cocktails
ENV MEDIA_ALIASES_PATH=/app/catalog/data/media-aliases.yaml

RUN mkdir -p /data

EXPOSE 8004

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8004/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
