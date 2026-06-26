"""Service + API tests for People Discovery (Module 5)."""

from __future__ import annotations

from careerpilot.backend.models.person import EmailSource, PersonRole
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.person import PersonRepository
from careerpilot.backend.schemas.company import CompanyCreate
from careerpilot.backend.schemas.person import PeopleSearchQuery, PersonUpdate
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.people import PeopleService


async def _make_company(session, **kw) -> int:
    service = CompanyService(CompanyRepository(session))
    company = await service.create(CompanyCreate(name=kw.pop("name", "Stripe"), **kw))
    return company.id


def _service(session) -> PeopleService:
    return PeopleService(CompanyRepository(session), PersonRepository(session))


async def test_discover_persists_people(session):
    cid = await _make_company(session, name="Stripe", domain="stripe.com")
    service = _service(session)

    people, saved = await service.discover_for_company(cid)

    assert saved == 2
    assert {p.full_name for p in people} == {"Maya Chen", "David Okafor"}
    maya = next(p for p in people if p.full_name == "Maya Chen")
    assert maya.email == "maya.chen@stripe.com"
    assert maya.email_source == EmailSource.PUBLIC
    assert maya.email_verified is False


async def test_discover_is_idempotent(session):
    cid = await _make_company(session, name="Stripe", domain="stripe.com")
    service = _service(session)

    await service.discover_for_company(cid)
    await service.discover_for_company(cid)  # run again

    people = await service.list_for_company(cid)
    assert len(people) == 2  # no duplicates on external_id


async def test_discover_does_not_downgrade_verified_email(session):
    cid = await _make_company(session, name="Stripe", domain="stripe.com")
    service = _service(session)

    people, _ = await service.discover_for_company(cid)
    maya = next(p for p in people if p.full_name == "Maya Chen")
    await service.update(maya.id, PersonUpdate(email_verified=True))

    # Re-running discovery must not flip verified back to False.
    await service.discover_for_company(cid)
    refreshed = await service.get(maya.id)
    assert refreshed.email_verified is True


async def test_list_filters_by_role(session):
    cid = await _make_company(session, name="Stripe", domain="stripe.com")
    service = _service(session)
    await service.discover_for_company(cid)

    recruiters = await service.list_for_company(
        cid, PeopleSearchQuery(role=PersonRole.RECRUITER)
    )
    assert {p.full_name for p in recruiters} == {"Maya Chen"}


async def test_api_discover_and_list_people(client):
    created = await client.post(
        "/api/v1/companies", json={"name": "Stripe", "domain": "stripe.com"}
    )
    cid = created.json()["id"]

    resp = await client.post(f"/api/v1/companies/{cid}/people/discover")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["people_saved"] == 2
    assert body["provider"] == "stub"
    assert len(body["people"]) == 2

    listed = await client.get(f"/api/v1/companies/{cid}/people?role=recruiter")
    assert listed.status_code == 200
    names = {p["full_name"] for p in listed.json()}
    assert names == {"Maya Chen"}


async def test_api_get_update_delete_person(client):
    created = await client.post(
        "/api/v1/companies", json={"name": "Stripe", "domain": "stripe.com"}
    )
    cid = created.json()["id"]
    discovered = await client.post(f"/api/v1/companies/{cid}/people/discover")
    person_id = discovered.json()["people"][0]["id"]

    got = await client.get(f"/api/v1/people/{person_id}")
    assert got.status_code == 200

    patched = await client.patch(
        f"/api/v1/people/{person_id}", json={"email_verified": True}
    )
    assert patched.status_code == 200
    assert patched.json()["email_verified"] is True

    deleted = await client.delete(f"/api/v1/people/{person_id}")
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/people/{person_id}")
    assert missing.status_code == 404


async def test_api_discover_missing_company_404(client):
    resp = await client.post("/api/v1/companies/999999/people/discover")
    assert resp.status_code == 404
