"""Tests for the stub people-discovery provider (Module 5)."""

from __future__ import annotations

from careerpilot.backend.models.person import EmailSource, PersonRole
from careerpilot.backend.schemas.person import PeopleSearchQuery
from careerpilot.backend.services.career_page.base import CompanyLike
from careerpilot.backend.services.people_discovery.base import get_provider
from careerpilot.backend.services.people_discovery.stub import StubPeopleProvider


async def test_provider_returns_curated_people_with_public_emails():
    provider = StubPeopleProvider()
    company = CompanyLike(name="Stripe", domain="stripe.com")
    results = await provider.discover(company, PeopleSearchQuery())

    names = {p.full_name for p in results}
    assert "Maya Chen" in names
    maya = next(p for p in results if p.full_name == "Maya Chen")
    assert maya.role == PersonRole.RECRUITER
    assert maya.email == "maya.chen@stripe.com"
    assert maya.email_source == EmailSource.PUBLIC
    assert maya.email_verified is False
    assert maya.source == "stub"


async def test_provider_synthesizes_unknown_company():
    provider = StubPeopleProvider()
    company = CompanyLike(name="Acme Robotics", domain="acmerobotics.com")
    results = await provider.discover(company, PeopleSearchQuery())

    assert len(results) == 3
    assert all(p.source == "stub:synthesized" for p in results)
    # External ids are deterministic and slug-based for idempotent upserts.
    assert {p.external_id for p in results} == {
        "acme-robotics-1",
        "acme-robotics-2",
        "acme-robotics-3",
    }


async def test_provider_without_domain_has_no_email():
    provider = StubPeopleProvider()
    results = await provider.discover(
        CompanyLike(name="No Domain Co"), PeopleSearchQuery()
    )
    assert results
    assert all(p.email is None for p in results)
    assert all(p.email_source == EmailSource.UNKNOWN for p in results)


async def test_provider_filters_by_role():
    provider = StubPeopleProvider()
    company = CompanyLike(name="Stripe", domain="stripe.com")
    results = await provider.discover(
        company, PeopleSearchQuery(role=PersonRole.RECRUITER)
    )
    assert results
    assert all(p.role == PersonRole.RECRUITER for p in results)


async def test_provider_respects_limit():
    provider = StubPeopleProvider()
    company = CompanyLike(name="Acme Robotics", domain="acmerobotics.com")
    results = await provider.discover(company, PeopleSearchQuery(limit=1))
    assert len(results) == 1


async def test_get_provider_defaults_to_stub():
    assert get_provider().name == "stub"
    assert get_provider("unknown-provider").name == "stub"
