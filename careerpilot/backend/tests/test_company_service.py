"""Service + API tests for Company Discovery (Module 3)."""

from __future__ import annotations

import pytest

from careerpilot.backend.core.exceptions import ConflictError, NotFoundError
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.schemas.company import (
    CompanyCreate,
    CompanySearchQuery,
    CompanyUpdate,
)
from careerpilot.backend.services.company import CompanyService


def _service(session) -> CompanyService:
    return CompanyService(CompanyRepository(session))


async def test_discover_persists_and_is_idempotent(session):
    service = _service(session)
    first = await service.discover(CompanySearchQuery(name="Stripe"))
    assert len(first) == 1
    assert first[0].id is not None

    # Re-discovering the same company updates in place — no duplicate row.
    again = await service.discover(CompanySearchQuery(name="Stripe"))
    assert again[0].id == first[0].id

    all_rows = await service._repo.list()
    assert sum(1 for c in all_rows if c.name == "Stripe") == 1


async def test_discover_then_search_db(session):
    service = _service(session)
    await service.discover(CompanySearchQuery(industry="Artificial Intelligence"))
    found = await service.search_db(CompanySearchQuery(name="Anthropic"))
    assert len(found) == 1
    assert found[0].industry == "Artificial Intelligence"


async def test_create_duplicate_raises_conflict(session):
    service = _service(session)
    await service.create(CompanyCreate(name="Acme"))
    with pytest.raises(ConflictError):
        await service.create(CompanyCreate(name="Acme"))


async def test_update_and_delete(session):
    service = _service(session)
    company = await service.create(CompanyCreate(name="Acme", tech_stack=["Python"]))
    updated = await service.update(
        company.id, CompanyUpdate(tech_stack=["Python", "Go"], hiring_platform="lever")
    )
    assert updated.tech_stack == "Python, Go"
    assert updated.hiring_platform == "lever"

    await service.delete(company.id)
    with pytest.raises(NotFoundError):
        await service.get(company.id)


async def test_api_discover_and_search(client):
    resp = await client.post("/api/v1/companies/discover", json={"name": "Vercel"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body[0]["name"] == "Vercel"
    assert "Next.js" in body[0]["tech_stack"]

    search = await client.get("/api/v1/companies/search", params={"name": "Vercel"})
    assert search.status_code == 200
    assert search.json()[0]["name"] == "Vercel"


async def test_api_crud_company(client):
    created = await client.post("/api/v1/companies", json={"name": "Globex"})
    assert created.status_code == 201
    cid = created.json()["id"]

    got = await client.get(f"/api/v1/companies/{cid}")
    assert got.status_code == 200

    patched = await client.patch(
        f"/api/v1/companies/{cid}", json={"industry": "Manufacturing"}
    )
    assert patched.json()["industry"] == "Manufacturing"

    assert (await client.delete(f"/api/v1/companies/{cid}")).status_code == 204
    assert (await client.get(f"/api/v1/companies/{cid}")).status_code == 404
