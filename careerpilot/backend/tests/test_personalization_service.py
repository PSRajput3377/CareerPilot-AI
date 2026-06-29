"""Service + API tests for the AI Personalization Engine (Module 12)."""

from __future__ import annotations

import pytest

from careerpilot.backend.core.exceptions import NotFoundError
from careerpilot.backend.models.job_listing import JobListing
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.email_template import EmailTemplateRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.job_match import JobMatchRepository
from careerpilot.backend.repositories.person import PersonRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.company import CompanyCreate
from careerpilot.backend.schemas.person import PersonCreate
from careerpilot.backend.schemas.personalization import PersonalizationRequest
from careerpilot.backend.schemas.user_profile import UserProfileCreate
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.job_matching import JobMatchingService
from careerpilot.backend.services.people import _to_model as person_to_model
from careerpilot.backend.services.personalization import PersonalizationService
from careerpilot.backend.services.subject import SubjectService
from careerpilot.backend.services.templating import EmailTemplateService
from careerpilot.backend.services.user_profile import UserProfileService


def _service(session) -> PersonalizationService:
    return PersonalizationService(
        UserProfileRepository(session),
        CompanyRepository(session),
        PersonRepository(session),
        JobListingRepository(session),
        JobMatchRepository(session),
        EmailTemplateRepository(session),
        SubjectService(
            UserProfileRepository(session),
            CompanyRepository(session),
            PersonRepository(session),
            JobListingRepository(session),
        ),
        EmailTemplateService(
            EmailTemplateRepository(session),
            UserProfileRepository(session),
            CompanyRepository(session),
            PersonRepository(session),
            JobListingRepository(session),
        ),
    )


async def _profile(session, **kw) -> int:
    service = UserProfileService(UserProfileRepository(session))
    profile = await service.create(
        UserProfileCreate(
            name=kw.pop("name", "Jane Engineer"),
            email=kw.pop("email", "jane@example.com"),
            preferred_role=kw.pop("preferred_role", "Backend Engineer"),
            skills=[{"name": s} for s in kw.pop("skills", ["Python", "FastAPI"])],
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


async def test_personalize_full_context(session):
    pid = await _profile(session)
    cid = await _company(session, name="Stripe", industry="Fintech")
    person_id = await _person(session, cid, full_name="Maya Chen")
    jid = await _listing(session, cid, title="Senior Backend Engineer")
    # Run matching so matched_skills are available.
    await JobMatchingService(
        UserProfileRepository(session),
        CompanyRepository(session),
        JobListingRepository(session),
        JobMatchRepository(session),
    ).match_company(pid, cid)

    service = _service(session)
    draft = await service.personalize(
        PersonalizationRequest(
            profile_id=pid, person_id=person_id, company_id=cid, job_listing_id=jid
        )
    )
    assert "Maya" in draft.body
    assert "Stripe" in draft.body
    assert "Senior Backend Engineer" in draft.body
    assert draft.matched_skills  # from the job match
    assert draft.personalization_score > 0.5
    assert draft.subject


async def test_company_defaults_to_persons_company(session):
    pid = await _profile(session)
    cid = await _company(session, name="Stripe")
    person_id = await _person(session, cid, full_name="Maya Chen")
    service = _service(session)

    # No company_id provided → resolved from the person.
    draft = await service.personalize(
        PersonalizationRequest(profile_id=pid, person_id=person_id)
    )
    assert "Stripe" in draft.body


async def test_personalize_with_template(session):
    pid = await _profile(session)
    cid = await _company(session, name="Stripe")
    person_id = await _person(session, cid, full_name="Maya Chen")
    # Seed built-ins and pick one.
    tpl_service = EmailTemplateService(
        EmailTemplateRepository(session),
        UserProfileRepository(session),
        CompanyRepository(session),
        PersonRepository(session),
        JobListingRepository(session),
    )
    templates = await tpl_service.list()
    cold = next(t for t in templates if t.name == "cold-outreach")

    service = _service(session)
    draft = await service.personalize(
        PersonalizationRequest(
            profile_id=pid, person_id=person_id, template_id=cold.id
        )
    )
    # Built-in greeting comes from the template.
    assert "Hi Maya" in draft.body


async def test_missing_person_raises(session):
    pid = await _profile(session)
    service = _service(session)
    with pytest.raises(NotFoundError):
        await service.personalize(
            PersonalizationRequest(profile_id=pid, person_id=999999)
        )


async def test_api_personalize(client):
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
        "/api/v1/companies", json={"name": "Stripe", "industry": "Fintech"}
    )
    cid = comp.json()["id"]
    disc = await client.post(f"/api/v1/companies/{cid}/people/discover")
    person_id = disc.json()["people"][0]["id"]

    resp = await client.post(
        "/api/v1/personalize",
        json={"profile_id": pid, "person_id": person_id, "company_id": cid},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["engine"] == "template"
    assert "Stripe" in body["body"]
    assert body["subject"]


async def test_api_personalize_missing_profile_404(client):
    comp = await client.post("/api/v1/companies", json={"name": "Stripe"})
    cid = comp.json()["id"]
    disc = await client.post(f"/api/v1/companies/{cid}/people/discover")
    person_id = disc.json()["people"][0]["id"]

    resp = await client.post(
        "/api/v1/personalize",
        json={"profile_id": 999999, "person_id": person_id, "company_id": cid},
    )
    assert resp.status_code == 404
