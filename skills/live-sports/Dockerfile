FROM python:3.12-slim-bookworm

WORKDIR /app

COPY shared/python /app/shared/python
COPY skills/live-sports/pyproject.toml /app/skills/live-sports/
COPY skills/live-sports/src /app/skills/live-sports/src

WORKDIR /app/skills/live-sports

RUN pip install --no-cache-dir \
    fastapi>=0.115.0 \
    "uvicorn[standard]>=0.32.0" \
    httpx>=0.27.0 \
    structlog>=24.4.0 \
    prometheus-client>=0.21.0 \
    pydantic>=2.9.0 \
    pydantic-settings>=2.6.0 \
    pyyaml>=6.0.0

ENV PYTHONPATH=/app/skills/live-sports/src:/app/shared/python

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
