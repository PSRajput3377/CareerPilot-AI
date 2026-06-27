"""Service + API tests for the Cover Letter Generator (Module 9)."""

from __future__ import annotations

import pytest

from careerpilot.backend.core.exceptions import NotFoundError
from careerpilot.backend.models.job_listing import JobListing
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.cover_letter import CoverLetterRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.job_match import JobMatchRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.company import CompanyCreate
from careerpilot.backend.schemas.cover_letter import CoverLetterRequest
from careerpilot.backend.schemas.user_profile import UserProfileCreate
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.cover_letter import CoverLetterService
from careerpilot.backend.services.user_profile import UserProfileService


async def _profile(session, **kw) -> int:
    service = UserProfileService(UserProfileRepository(session))
    payload = UserProfileCreate(
        name=kw.pop("name", "Jane Engineer"),
        email=kw.pop("email", "jane@example.com"),
        preferred_role=kw.pop("preferred_role", "Backend Engineer"),
        skills=[{"name": s} for s in kw.pop("skills", ["Python", "FastAPI"])],
    )
    profile = await service.create(payload)
    return profile.id


async def _company(session, **kw) -> int:
    service = CompanyService(CompanyRepository(session))
    company = await service.create(CompanyCreate(name=kw.pop("name", "Acme"), **kw))
    return company.id


async def _listing(session, company_id: int, **kw) -> int:
    repo = JobListingRepository(session)
    listing = await repo.add(
        JobListing(
            company_id=company_id,
            title=kw.pop("title", "Backend Engineer"),
            description=kw.pop("description", "Python and FastAPI."),
        )
    )
    return listing.id


def _service(session) -> CoverLetterService:
    return CoverLetterService(
        UserProfileRepository(session),
        CompanyRepository(session),
        JobListingRepository(session),
        CoverLetterRepository(session),
        JobMatchRepository(session),
    )


async def test_generate_and_persist(session):
    pid = await _profile(session)
    cid = await _company(session, name="Acme", industry="Fintech")
    service = _service(session)

    draft, saved = await service.generate(pid, CoverLetterRequest(company_id=cid))

    assert saved is not None
    assert saved.id is not None
    assert "Acme" in draft.body
    assert saved.body == draft.body
    assert saved.generator == "template"

    listed = await service.list_for_profile(pid)
    assert len(listed) == 1


async def test_preview_does_not_persist(session):
    pid = await _profile(session)
    cid = await _company(session, name="Acme")
    service = _service(session)

    draft, saved = await service.generate(
        pid, CoverLetterRequest(company_id=cid, save=False)
    )
    assert saved is None
    assert draft.body
    assert await service.list_for_profile(pid) == []


async def test_generate_for_specific_listing_uses_role(session):
    pid = await _profile(session)
    cid = await _company(session, name="Acme")
    jid = await _listing(session, cid, title="Staff Platform Engineer")
    service = _service(session)

    draft, _ = await service.generate(
        pid, CoverLetterRequest(company_id=cid, job_listing_id=jid)
    )
    assert "Staff Platform Engineer" in draft.body


async def test_listing_from_other_company_raises(session):
    pid = await _profile(session)
    cid1 = await _company(session, name="Acme", domain="acme.com")
    cid2 = await _company(session, name="Globex", domain="globex.com")
    jid = await _listing(session, cid2, title="Engineer")
    service = _service(session)

    with pytest.raises(NotFoundError):
        await service.generate(
            pid, CoverLetterRequest(company_id=cid1, job_listing_id=jid)
        )


async def test_delete_cover_letter(session):
    pid = await _profile(session)
    cid = await _company(session, name="Acme")
    service = _service(session)
    _, saved = await service.generate(pid, CoverLetterRequest(company_id=cid))

    await service.delete(saved.id)
    with pytest.raises(NotFoundError):
        await service.get(saved.id)


async def test_api_generate_list_get_delete(client):
    prof = await client.post(
        "/api/v1/profiles",
        json={
            "name": "Jane Engineer",
            "email": "jane@example.com",
            "preferred_role": "Backend Engineer",
            "skills": [{"name": "Python"}],
        },
    )
    pid = prof.json()["id"]
    comp = await client.post(
        "/api/v1/companies", json={"name": "Acme", "industry": "Fintech"}
    )
    cid = comp.json()["id"]

    gen = await client.post(
        f"/api/v1/profiles/{pid}/cover-letters",
        json={"company_id": cid, "tone": "enthusiastic"},
    )
    assert gen.status_code == 200, gen.text
    body = gen.json()
    assert body["tone"] == "enthusiastic"
    assert "Acme" in body["body"]
    letter_id = body["id"]

    listed = await client.get(f"/api/v1/profiles/{pid}/cover-letters")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    got = await client.get(f"/api/v1/cover-letters/{letter_id}")
    assert got.status_code == 200

    deleted = await client.delete(f"/api/v1/cover-letters/{letter_id}")
    assert deleted.status_code == 204


async def test_api_generate_preview(client):
    prof = await client.post(
        "/api/v1/profiles", json={"name": "Sam", "email": "sam@example.com"}
    )
    pid = prof.json()["id"]
    comp = await client.post("/api/v1/companies", json={"name": "Globex"})
    cid = comp.json()["id"]

    resp = await client.post(
        f"/api/v1/profiles/{pid}/cover-letters",
        json={"company_id": cid, "save": False},
    )
    assert resp.status_code == 200, resp.text
    # Preview has no id field.
    assert "id" not in resp.json()
    # Nothing persisted.
    listed = await client.get(f"/api/v1/profiles/{pid}/cover-letters")
    assert listed.json() == []


async def test_api_generate_missing_company_404(client):
    prof = await client.post(
        "/api/v1/profiles", json={"name": "Sam", "email": "sam@example.com"}
    )
    pid = prof.json()["id"]
    resp = await client.post(
        f"/api/v1/profiles/{pid}/cover-letters", json={"company_id": 999999}
    )
    assert resp.status_code == 404
