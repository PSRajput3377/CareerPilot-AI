"""Unit tests for the offline heuristic email verifier (Module 7)."""

from __future__ import annotations

import pytest

from careerpilot.backend.models.email_verification import VerificationStatus
from careerpilot.backend.services.email_verification.base import get_verifier
from careerpilot.backend.services.email_verification.heuristic import (
    HeuristicEmailVerifier,
)


@pytest.fixture
def verifier() -> HeuristicEmailVerifier:
    return HeuristicEmailVerifier()


async def test_valid_business_email(verifier):
    outcome = await verifier.verify("jane.doe@stripe.com")
    assert outcome.status == VerificationStatus.VALID
    assert outcome.syntax_ok and outcome.domain_ok and outcome.mx_found
    assert outcome.is_valid


async def test_malformed_email_is_invalid(verifier):
    for bad in ["not-an-email", "two@@at.com", "no-at-sign.com", "trailing@dot."]:
        outcome = await verifier.verify(bad)
        assert outcome.status == VerificationStatus.INVALID, bad
        assert not outcome.is_valid


async def test_empty_email_is_unknown(verifier):
    outcome = await verifier.verify("")
    assert outcome.status == VerificationStatus.UNKNOWN
    assert outcome.reason


async def test_disposable_domain_is_risky(verifier):
    outcome = await verifier.verify("jane.doe@mailinator.com")
    assert outcome.status == VerificationStatus.RISKY
    assert outcome.is_disposable


async def test_role_account_is_risky(verifier):
    outcome = await verifier.verify("careers@acme.com")
    assert outcome.status == VerificationStatus.RISKY
    assert outcome.is_role_account


async def test_role_account_with_plus_tag(verifier):
    outcome = await verifier.verify("info+jobs@acme.com")
    assert outcome.is_role_account


async def test_known_consumer_domain_valid(verifier):
    outcome = await verifier.verify("someone@gmail.com")
    assert outcome.status == VerificationStatus.VALID


async def test_get_verifier_defaults_to_heuristic():
    assert get_verifier().name == "heuristic"
    assert get_verifier("unknown").name == "heuristic"
