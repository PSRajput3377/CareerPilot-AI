"""Tests for the stub discovery provider (Module 3)."""

from __future__ import annotations

from careerpilot.backend.models.company import FundingStage, HiringStatus
from careerpilot.backend.schemas.company import CompanySearchQuery
from careerpilot.backend.services.company_discovery.base import get_provider
from careerpilot.backend.services.company_discovery.stub import StubCompanyProvider


async def test_provider_returns_known_company():
    provider = StubCompanyProvider()
    results = await provider.discover(CompanySearchQuery(name="Stripe"))
    assert len(results) == 1
    assert results[0].name == "Stripe"
    assert results[0].domain == "stripe.com"
    assert "Go" in results[0].tech_stack
    assert results[0].source == "stub"


async def test_provider_synthesizes_unknown_company():
    provider = StubCompanyProvider()
    results = await provider.discover(CompanySearchQuery(name="Acme Robotics"))
    assert len(results) == 1
    assert results[0].domain == "acmerobotics.com"
    assert results[0].source == "stub:synthesized"
    assert results[0].hiring_status == HiringStatus.UNKNOWN


async def test_provider_filters_by_industry():
    provider = StubCompanyProvider()
    results = await provider.discover(CompanySearchQuery(industry="Artificial Intelligence"))
    names = {c.name for c in results}
    assert "Anthropic" in names
    assert "Stripe" not in names


async def test_provider_filters_by_funding_stage():
    provider = StubCompanyProvider()
    results = await provider.discover(CompanySearchQuery(funding_stage=FundingStage.PUBLIC))
    assert all(c.funding_stage == FundingStage.PUBLIC for c in results)
    assert "Datadog" in {c.name for c in results}


async def test_get_provider_defaults_to_stub():
    assert get_provider().name == "stub"
    assert get_provider("unknown-provider").name == "stub"
