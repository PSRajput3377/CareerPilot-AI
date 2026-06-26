"""Service + API tests for the Email Pattern Generator (Module 6)."""

from __future__ import annotations

from careerpilot.backend.models.person import EmailSource
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.person import PersonRepository
from careerpilot.backend.schemas.company import CompanyCreate
from careerpilot.backend.schemas.person import PersonCreate
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.email_pattern import EmailPatternService
from careerpilot.backend.services.people import PeopleService


async def _company(session, **kw) -> int:
    service = CompanyService(CompanyRepository(session))
    company = await service.create(CompanyCreate(name=kw.pop("name", "Acme"), **kw))
    return company.id


async def _person(session, company_id: int, **kw):
    repo = PersonRepository(session)
    service = PeopleService(CompanyRepository(session), repo)
    # Insert directly via the repo through an upsert-style create.
    from careerpilot.backend.services.people import _to_model

    person = await repo.add(_to_model(company_id, PersonCreate(**kw)))
    return person, service


def _service(session) -> EmailPatternService:
    return EmailPatternService(CompanyRepository(session), PersonRepository(session))


async def test_guess_fills_missing_email(session):
    cid = await _company(session, name="Acme", domain="acme.com")
    person, _ = await _person(session, cid, full_name="Jane Doe")
    service = _service(session)

    result = await service.guess_for_person(person.id)

    assert result.filled is True
    assert result.email == "jane.doe@acme.com"
    refreshed = await PeopleService(
        CompanyRepository(session), PersonRepository(session)
    ).get(person.id)
    assert refreshed.email == "jane.doe@acme.com"
    assert refreshed.email_source == EmailSource.PATTERN
    assert refreshed.email_verified is False


async def test_guess_does_not_overwrite_public_email(session):
    cid = await _company(session, name="Acme", domain="acme.com")
    person, _ = await _person(
        session,
        cid,
        full_name="Jane Doe",
        email="jane@public.acme.com",
        email_source=EmailSource.PUBLIC,
    )
    service = _service(session)

    result = await service.guess_for_person(person.id)
    assert result.filled is False
    assert result.email == "jane@public.acme.com"


async def test_guess_overwrite_replaces_existing_guess(session):
    cid = await _company(session, name="Acme", domain="acme.com")
    person, _ = await _person(
        session,
        cid,
        full_name="Jane Doe",
        email="old.guess@acme.com",
        email_source=EmailSource.PATTERN,
    )
    service = _service(session)

    # Without overwrite, an existing guess is left alone.
    assert (await service.guess_for_person(person.id)).filled is False
    # With overwrite, it is regenerated.
    result = await service.guess_for_person(person.id, overwrite=True)
    assert result.filled is True
    assert result.email == "jane.doe@acme.com"


async def test_guess_no_domain_does_not_fill(session):
    cid = await _company(session, name="NoDomain")  # no domain/website
    person, _ = await _person(session, cid, full_name="Jane Doe")
    service = _service(session)

    result = await service.guess_for_person(person.id)
    assert result.filled is False
    assert result.email is None
    assert result.candidates == []


async def test_guess_uses_website_when_domain_missing(session):
    cid = await _company(session, name="Acme", website="https://www.acme.io/about")
    person, _ = await _person(session, cid, full_name="Jane Doe")
    service = _service(session)

    result = await service.guess_for_person(person.id)
    assert result.filled is True
    assert result.email == "jane.doe@acme.io"


async def test_api_preview_and_company_guess(client):
    # Preview is stateless.
    preview = await client.get(
        "/api/v1/email-patterns/preview",
        params={"full_name": "Jane Doe", "domain": "acme.com"},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["candidates"][0]["email"] == "jane.doe@acme.com"

    # Set up a company + discovered people, then fill emails.
    created = await client.post(
        "/api/v1/companies", json={"name": "Acme Corp", "domain": "acmecorp.com"}
    )
    cid = created.json()["id"]
    await client.post(f"/api/v1/companies/{cid}/people/discover")

    resp = await client.post(f"/api/v1/companies/{cid}/people/guess-emails")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Synthesized people have no email yet, so all should be filled.
    assert body
    assert all(r["email"] and r["email"].endswith("@acmecorp.com") for r in body)


async def test_api_guess_person(client):
    created = await client.post(
        "/api/v1/companies", json={"name": "Acme", "domain": "acme.com"}
    )
    cid = created.json()["id"]
    discovered = await client.post(f"/api/v1/companies/{cid}/people/discover")
    # Pick a synthesized person that lacks an email.
    pid = discovered.json()["people"][0]["id"]
    # Clear any email so the guess applies deterministically.
    await client.patch(f"/api/v1/people/{pid}", json={"email": None})

    resp = await client.post(f"/api/v1/people/{pid}/guess-email")
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"].endswith("@acme.com")
