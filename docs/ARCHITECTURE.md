# Architecture

CareerPilot AI follows **Clean Architecture**: dependencies point inward, and
each concern lives in one layer. Entrypoints (API, CLI, workers) are thin and
delegate to the same service layer, so behaviour is identical regardless of how
a feature is invoked.

## Layers

```
            ┌─────────────────────────────────────────────┐
 Entry      │   FastAPI router (api/)   Typer CLI (cli.py) │
 points     │   Celery workers (workers/)                  │
            └───────────────────────┬─────────────────────┘
                                     │ depends on
            ┌────────────────────────▼────────────────────┐
 Application│   Services (services/)  ← business rules     │
            └────────────────────────┬────────────────────┘
                                     │ depends on
            ┌────────────────────────▼────────────────────┐
 Domain     │   Repositories (repositories/)  ← data access│
 / Data     │   Models (models/)              ← ORM        │
            └────────────────────────┬────────────────────┘
                                     │
            ┌────────────────────────▼────────────────────┐
 Infra      │  Database (database/)  Config (config/)      │
            │  Security/Logging (core/)  Templates/Utils   │
            └─────────────────────────────────────────────┘

 Contracts: Schemas (schemas/) — Pydantic request/response models, the boundary
            between transport and domain. ORM objects never cross the API edge.
```

### Responsibilities

| Layer | Package | Rule |
| ----- | ------- | ---- |
| Schemas | `schemas/` | Validate input, shape output. No DB/IO. |
| Models | `models/` | SQLAlchemy ORM. Persistence shape only. |
| Repositories | `repositories/` | All queries. Return ORM objects. No business rules. |
| Services | `services/` | Business rules + orchestration. Raise domain exceptions. |
| API | `api/` | HTTP transport. Map domain exceptions → status codes. |
| CLI | `cli.py` | Terminal transport. Calls services directly. |
| Core | `core/` | Cross-cutting: security, logging, exceptions. |
| Config | `config/` | Layered settings (YAML + env). |

## Request flow (Module 1 example)

```
POST /api/v1/profiles
  → profiles.create_profile (router)
     → UserProfileServiceDep  (DI: builds repo over request session)
        → UserProfileService.create   (dedupe skills, conflict check)
           → UserProfileRepository.add (flush + refresh)
        ← UserProfile (ORM)
     ← UserProfileRead.model_validate(...)   (ORM → schema)
  ← 201 JSON
```

Domain errors (`NotFoundError`, `ConflictError`, `ValidationError`) are raised
in the service and translated centrally in `api/errors.py` — HTTP status codes
never leak into business logic.

## Design principles applied

- **SOLID** — single-responsibility layers; services depend on repository
  abstractions (DIP); `BaseRepository` is open for extension.
- **Dependency Injection** — `api/dependencies.py` wires repos into services;
  the session is request-scoped via `get_db`.
- **Repository Pattern** — `BaseRepository[ModelT]` provides generic CRUD;
  feature repos add aggregate-specific queries.
- **Async-first** — async SQLAlchemy 2.0 + FastAPI; CLI bridges via `asyncio.run`.
- **Configuration & secrets** — non-secret config in `config.yaml`, secrets in
  env/`.env`, secrets encrypted at rest with Fernet.

## The outreach orchestration contract

The end-to-end pipeline (see README) is the north star for module design:

```
discover → verify → draft → REVIEW (human gate) → send → track → follow-up
```

Key invariants every future module must respect:

1. **Human-in-the-loop**: outreach is drafted into a reviewable state; sending
   is a separate explicit action — never automatic.
2. **Verified-email-first**: a known public business email is preferred over a
   generated pattern; unverified addresses are not sent to by default.
3. **Rate limits & retries** are centralized in config and honored by the
   sender/scheduler.

## Extensibility (Module 23)

New capabilities (LinkedIn assistant, ATS checker, notifications, browser
extension, …) attach as new `services/` + `repositories/` + `api/v1/` routers
without touching existing modules. The v1 router aggregates feature routers in
one place (`api/v1/__init__.py`), and the CLI registers command groups
similarly, so the surface grows additively.
