"""Service + API tests for the Email Template Engine (Module 10)."""

from __future__ import annotations

import pytest

from careerpilot.backend.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from careerpilot.backend.models.job_listing import JobListing
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.email_template import EmailTemplateRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.person import PersonRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.company import CompanyCreate
from careerpilot.backend.schemas.email_template import (
    EmailTemplateCreate,
    EmailTemplateUpdate,
    RenderContext,
)
from careerpilot.backend.schemas.person import PersonCreate
from careerpilot.backend.schemas.user_profile import UserProfileCreate
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.people import _to_model as person_to_model
from careerpilot.backend.services.templating import EmailTemplateService
from careerpilot.backend.services.user_profile import UserProfileService


def _service(session) -> EmailTemplateService:
    return EmailTemplateService(
        EmailTemplateRepository(session),
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


# -- seeding & CRUD ------------------------------------------------------- #


async def test_seed_builtins_is_idempotent(session):
    service = _service(session)
    first = await service.seed_builtins()
    second = await service.seed_builtins()
    assert first > 0
    assert second == 0
    templates = await service.list()
    assert any(t.name == "cold-outreach" for t in templates)


async def test_create_and_get_custom_template(session):
    service = _service(session)
    created = await service.create(
        EmailTemplateCreate(
            name="my-tpl",
            subject_template="Hi {first_name}",
            body_template="Hello {first_name} at {company}.",
        )
    )
    assert created.id is not None
    assert created.is_builtin is False
    fetched = await service.get(created.id)
    assert fetched.name == "my-tpl"


async def test_duplicate_name_conflicts(session):
    service = _service(session)
    await service.create(
        EmailTemplateCreate(name="dup", subject_template="s", body_template="b")
    )
    with pytest.raises(ConflictError):
        await service.create(
            EmailTemplateCreate(name="dup", subject_template="s2", body_template="b2")
        )


async def test_builtin_cannot_be_edited_or_deleted(session):
    service = _service(session)
    await service.seed_builtins()
    templates = await service.list()
    builtin = next(t for t in templates if t.is_builtin)

    with pytest.raises(ValidationError):
        await service.update(builtin.id, EmailTemplateUpdate(description="x"))
    with pytest.raises(ValidationError):
        await service.delete(builtin.id)


async def test_update_and_delete_custom(session):
    service = _service(session)
    created = await service.create(
        EmailTemplateCreate(name="c", subject_template="s", body_template="b")
    )
    updated = await service.update(
        created.id, EmailTemplateUpdate(description="updated")
    )
    assert updated.description == "updated"
    await service.delete(created.id)
    with pytest.raises(NotFoundError):
        await service.get(created.id)


# -- rendering ------------------------------------------------------------ #


async def test_render_resolves_context(session):
    pid = await _profile(session, name="Jane Engineer", preferred_role="Backend Engineer")
    cid = await _company(session, name="Stripe", industry="Fintech")
    person_id = await _person(session, cid, full_name="Maya Chen")
    service = _service(session)
    tpl = await service.create(
        EmailTemplateCreate(
            name="r",
            subject_template="{candidate_name} -> {company}",
            body_template="Hi {first_name} ({last_name}), re {role} at {company}.",
        )
    )

    rendered = await service.render(
        tpl.id, RenderContext(profile_id=pid, company_id=cid, person_id=person_id)
    )
    assert rendered.subject == "Jane Engineer -> Stripe"
    assert "Hi Maya (Chen)" in rendered.body
    assert "Backend Engineer at Stripe" in rendered.body
    assert rendered.missing_placeholders == []


async def test_render_uses_job_listing_role(session):
    pid = await _profile(session)
    cid = await _company(session, name="Stripe")
    repo = JobListingRepository(session)
    listing = await repo.add(
        JobListing(company_id=cid, title="Staff Platform Engineer")
    )
    service = _service(session)
    tpl = await service.create(
        EmailTemplateCreate(name="r2", subject_template="s", body_template="Role: {role}")
    )
    rendered = await service.render(
        tpl.id,
        RenderContext(profile_id=pid, company_id=cid, job_listing_id=listing.id),
    )
    assert "Staff Platform Engineer" in rendered.body


async def test_render_reports_missing_placeholders(session):
    pid = await _profile(session)
    service = _service(session)
    tpl = await service.create(
        EmailTemplateCreate(
            name="r3",
            subject_template="s",
            body_template="Hi {first_name} at {company}",
        )
    )
    # No company/person in context → those placeholders are missing.
    rendered = await service.render(tpl.id, RenderContext(profile_id=pid))
    assert set(rendered.missing_placeholders) == {"first_name", "company"}
    assert "{first_name}" in rendered.body


# -- API ------------------------------------------------------------------ #


async def test_api_list_create_render(client):
    # Built-ins are auto-seeded on list.
    listed = await client.get("/api/v1/email-templates")
    assert listed.status_code == 200
    assert any(t["name"] == "cold-outreach" for t in listed.json())

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

    created = await client.post(
        "/api/v1/email-templates",
        json={
            "name": "api-tpl",
            "subject_template": "Hi from {candidate_name}",
            "body_template": "Interested in {company}.",
        },
    )
    assert created.status_code == 201, created.text
    tid = created.json()["id"]

    rendered = await client.post(
        f"/api/v1/email-templates/{tid}/render",
        json={"profile_id": pid, "company_id": cid},
    )
    assert rendered.status_code == 200, rendered.text
    body = rendered.json()
    assert body["subject"] == "Hi from Jane Engineer"
    assert "Interested in Stripe." == body["body"]


async def test_api_builtin_delete_rejected(client):
    listed = await client.get("/api/v1/email-templates")
    builtin = next(t for t in listed.json() if t["is_builtin"])
    resp = await client.delete(f"/api/v1/email-templates/{builtin['id']}")
    assert resp.status_code == 422
