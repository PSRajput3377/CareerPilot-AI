"""Service + API tests for the Subject Generator (Module 11)."""

from __future__ import annotations

import pytest

from careerpilot.backend.core.exceptions import NotFoundError
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.person import PersonRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.company import CompanyCreate
from careerpilot.backend.schemas.person import PersonCreate
from careerpilot.backend.schemas.subject import SubjectRequest
from careerpilot.backend.schemas.user_profile import UserProfileCreate
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.people import _to_model as person_to_model
from careerpilot.backend.services.subject import SubjectService
from careerpilot.backend.services.user_profile import UserProfileService


def _service(session) -> SubjectService:
    return SubjectService(
        UserProfileRepository(session),
        CompanyRepository(session),
        PersonRepository(session),
        JobListingRepository(session),
    )


async def _profile(session, **kw) -> int:
    service = UserProfileService(UserProfileRepository(session))
    profile = await service.create(
        UserProfileCreate(
            name=kw.pop("name", "Jane Engineer"),
            email=kw.pop("email", "jane@example.com"),
            preferred_role=kw.pop("preferred_role", "Backend Engineer"),
        )
    )
    return profile.id


async def _company(session, **kw) -> int:
    service = CompanyService(CompanyRepository(session))
    company = await service.create(CompanyCreate(name=kw.pop("name", "Stripe"), **kw))
    return company.id


async def _person(session, company_id: int, **kw) -> int:
    repo = PersonRepository(session)
    person = await repo.add(
        person_to_model(company_id, PersonCreate(full_name=kw.pop("full_name", "Maya Chen")))
    )
    return person.id


async def test_generate_with_full_context(session):
    pid = await _profile(session)
    cid = await _company(session, name="Stripe")
    person_id = await _person(session, cid, full_name="Maya Chen")
    service = _service(session)

    result = await service.generate(
        SubjectRequest(profile_id=pid, company_id=cid, person_id=person_id)
    )
    assert result.candidates
    joined = " ".join(c.text for c in result.candidates)
    assert "Stripe" in joined
    # Referral style appears because a recipient name is present.
    assert any(c.style.value == "referral" for c in result.candidates)


async def test_job_listing_role_overrides_preferred(session):
    pid = await _profile(session, preferred_role="Backend Engineer")
    cid = await _company(session, name="Stripe")
    from careerpilot.backend.models.job_listing import JobListing

    repo = JobListingRepository(session)
    listing = await repo.add(
        JobListing(company_id=cid, title="Staff Platform Engineer")
    )
    service = _service(session)

    result = await service.generate(
        SubjectRequest(profile_id=pid, company_id=cid, job_listing_id=listing.id)
    )
    joined = " ".join(c.text for c in result.candidates)
    assert "Staff Platform Engineer" in joined


async def test_minimal_context_profile_only(session):
    pid = await _profile(session)
    service = _service(session)
    result = await service.generate(SubjectRequest(profile_id=pid))
    assert result.candidates


async def test_missing_profile_raises(session):
    service = _service(session)
    with pytest.raises(NotFoundError):
        await service.generate(SubjectRequest(profile_id=999999))


async def test_api_generate_subjects(client):
    prof = await client.post(
        "/api/v1/profiles",
        json={
            "name": "Jane Engineer",
            "email": "jane@example.com",
            "preferred_role": "Backend Engineer",
        },
    )
    pid = prof.json()["id"]
    comp = await client.post("/api/v1/companies", json={"name": "Stripe"})
    cid = comp.json()["id"]

    resp = await client.post(
        "/api/v1/subjects/generate",
        json={"profile_id": pid, "company_id": cid, "limit": 3},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["generator"] == "template"
    assert 1 <= len(body["candidates"]) <= 3
    assert all("Stripe" in c["text"] or c["text"] for c in body["candidates"])


async def test_api_missing_company_404(client):
    prof = await client.post(
        "/api/v1/profiles", json={"name": "Sam", "email": "sam@example.com"}
    )
    pid = prof.json()["id"]
    resp = await client.post(
        "/api/v1/subjects/generate", json={"profile_id": pid, "company_id": 999999}
    )
    assert resp.status_code == 404
