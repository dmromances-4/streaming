FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY shared/python /app/shared/python
COPY skills/storage-hls/pyproject.toml /app/skills/storage-hls/
COPY skills/storage-hls/src /app/skills/storage-hls/src

WORKDIR /app/skills/storage-hls

RUN pip install --no-cache-dir \
    fastapi>=0.115.0 \
    "uvicorn[standard]>=0.32.0" \
    structlog>=24.4.0 \
    prometheus-client>=0.21.0 \
    pydantic>=2.9.0 \
    pydantic-settings>=2.6.0 \
    boto3>=1.35.0 \
    httpx>=0.27.0 \
    aiosqlite>=0.20.0

ENV PYTHONPATH=/app/skills/storage-hls/src:/app/shared/python
ENV HLS_WORK_DIR=/tmp/hls-jobs
ENV JOBS_DB_PATH=/data/hls-jobs.db

RUN mkdir -p /tmp/hls-jobs /data

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
