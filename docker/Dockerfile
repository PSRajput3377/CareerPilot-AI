# CareerPilot AI — application image
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (build tools for any wheels that need compiling).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for layer caching.
COPY pyproject.toml README.md ./
COPY careerpilot ./careerpilot
RUN pip install --upgrade pip && pip install ".[email,workers]"

# Non-root runtime user.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "careerpilot.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
