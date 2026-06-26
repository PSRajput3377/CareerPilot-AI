# Deployment & Docker

## Local development

SQLite, auto-created tables, ephemeral encryption key — zero setup:

```bash
pip install -e ".[dev]"
careerpilot init-db
uvicorn careerpilot.backend.main:app --reload
```

## Docker (production-like)

```bash
# One-time: mint a real encryption key and export it.
export CAREERPILOT_ENCRYPTION_KEY=$(python -m careerpilot.backend.core.security generate-key)

# Build and run API + PostgreSQL + Redis.
docker compose -f docker/docker-compose.yml up --build
```

The API is served at `http://localhost:8000` (`/docs` for Swagger UI).

## Production checklist

- [ ] `CAREERPILOT_ENV=production`
- [ ] `CAREERPILOT_ENCRYPTION_KEY` set (app refuses to encrypt without it)
- [ ] `CAREERPILOT_DATABASE_URL` → managed PostgreSQL (`postgresql+asyncpg://…`)
- [ ] Run Alembic migrations (production does **not** auto-create tables)
- [ ] Provider credentials (SMTP / SES / Gmail / Graph) supplied via env/secrets
- [ ] Run behind a process manager / orchestrator with multiple Uvicorn workers
- [ ] Logs shipped from `careerpilot/backend/logs/` (or stdout) to your platform

## Migrations (Alembic)

Alembic is included as a dependency; the migration environment and the first
revision are introduced with the modules that add persistent tables beyond
Module 1. Until then, `careerpilot init-db` bootstraps the schema for dev.

## CI

GitHub Actions runs lint + type-check + tests on every push (see
`.github/workflows/ci.yml`).
