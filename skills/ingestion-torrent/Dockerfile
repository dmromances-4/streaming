FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libtorrent-rasterbar-dev \
    libboost-all-dev \
    && pip install --no-cache-dir python-libtorrent \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY shared/python /app/shared/python
COPY skills/ingestion-torrent/pyproject.toml /app/skills/ingestion-torrent/
COPY skills/ingestion-torrent/src /app/skills/ingestion-torrent/src

WORKDIR /app/skills/ingestion-torrent

RUN pip install --no-cache-dir \
    fastapi>=0.115.0 \
    "uvicorn[standard]>=0.32.0" \
    structlog>=24.4.0 \
    prometheus-client>=0.21.0 \
    pydantic>=2.9.0 \
    pydantic-settings>=2.6.0

ENV PYTHONPATH=/app/skills/ingestion-torrent/src:/app/shared/python
ENV TORRENT_CACHE_DIR=/tmp/torrent-cache

RUN mkdir -p /tmp/torrent-cache

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
