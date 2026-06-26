# Developer Guide

How to add a feature module without refactoring existing ones. The User Profile
module (Module 1) is the reference implementation — copy its shape.

## Anatomy of a module

For a feature `Foo`, create these files:

```
models/foo.py           # SQLAlchemy ORM model(s)
schemas/foo.py          # Pydantic FooCreate / FooUpdate / FooRead
repositories/foo.py     # FooRepository(BaseRepository[Foo]) + queries
services/foo.py         # FooService — business rules, raises domain errors
api/v1/foo.py           # APIRouter with prefix="/foo"
tests/test_foo_*.py     # service (unit) + api (integration) tests
```

Then wire them up in three existing files:

1. `models/__init__.py` — import the model so it registers on `Base.metadata`.
2. `api/dependencies.py` — add a `get_foo_service` provider + `FooServiceDep`.
3. `api/v1/__init__.py` — `api_router.include_router(foo.router)`.
4. (optional) `cli.py` — add a Typer sub-app or replace the stub command.

## Rules

- **Services raise domain exceptions** (`core/exceptions.py`), never `HTTPException`.
  `api/errors.py` maps them to status codes once.
- **Repositories own all queries.** Services never touch the session directly
  for queries (they may build ORM objects).
- **Schemas are the API boundary.** Convert ORM → schema with
  `FooRead.model_validate(obj)` in the router; never return ORM objects.
- **Async everywhere** in services/repos. The CLI bridges with `asyncio.run`.
- **Type hints + docstrings** on every public function.
- **Tests before moving on**: at least one service unit test and one API
  integration test per module; keep the suite green.

## Running things

```bash
pytest                                   # tests
uvicorn careerpilot.backend.main:app --reload   # API + /docs
careerpilot --help                       # CLI
ruff check careerpilot                    # lint
mypy careerpilot                          # type-check
```

## Respecting the orchestration contract

If a module participates in outreach, honor the invariants in
[ARCHITECTURE.md](ARCHITECTURE.md#the-outreach-orchestration-contract):
draft → review → send (never auto-send), verified-email-first, centralized
rate limits/retries.
