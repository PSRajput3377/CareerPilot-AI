"""Service + API tests for Email Verification (Module 7)."""

from __future__ import annotations

import pytest

from careerpilot.backend.core.exceptions import ValidationError
from careerpilot.backend.models.email_verification import VerificationStatus
from careerpilot.backend.models.person import EmailSource
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.email_verification import (
    EmailVerificationRepository,
)
from careerpilot.backend.repositories.person import PersonRepository
from careerpilot.backend.schemas.company import CompanyCreate
from careerpilot.backend.schemas.person import PersonCreate
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.email_verification import EmailVerificationService
from careerpilot.backend.services.people import _to_model


async def _company(session, **kw) -> int:
    service = CompanyService(CompanyRepository(session))
    company = await service.create(CompanyCreate(name=kw.pop("name", "Acme"), **kw))
    return company.id


async def _person(session, company_id: int, **kw):
    repo = PersonRepository(session)
    return await repo.add(_to_model(company_id, PersonCreate(**kw)))


def _service(session) -> EmailVerificationService:
    return EmailVerificationService(
        CompanyRepository(session),
        PersonRepository(session),
        EmailVerificationRepository(session),
    )


async def test_verify_valid_email_sets_flag(session):
    cid = await _company(session, name="Acme", domain="acme.com")
    person = await _person(
        session,
        cid,
        full_name="Jane Doe",
        email="jane.doe@acme.com",
        email_source=EmailSource.PATTERN,
    )
    service = _service(session)

    result = await service.verify_person(person.id)

    assert result.outcome.status == VerificationStatus.VALID
    assert result.email_verified is True
    refreshed = await PersonRepository(session).get(person.id)
    assert refreshed.email_verified is True

    # A verification record was persisted.
    records = await service.list_for_person(person.id)
    assert len(records) == 1
    assert records[0].email == "jane.doe@acme.com"


async def test_verify_risky_does_not_set_flag(session):
    cid = await _company(session, name="Acme", domain="acme.com")
    person = await _person(
        session, cid, full_name="Careers Team", email="careers@acme.com"
    )
    service = _service(session)

    result = await service.verify_person(person.id)
    assert result.outcome.status == VerificationStatus.RISKY
    assert result.email_verified is False


async def test_verify_is_idempotent(session):
    cid = await _company(session, name="Acme", domain="acme.com")
    person = await _person(
        session, cid, full_name="Jane Doe", email="jane.doe@acme.com"
    )
    service = _service(session)

    await service.verify_person(person.id)
    await service.verify_person(person.id)  # re-run

    records = await service.list_for_person(person.id)
    assert len(records) == 1  # no duplicate for the same (person, email)


async def test_verify_person_without_email_raises(session):
    cid = await _company(session, name="Acme", domain="acme.com")
    person = await _person(session, cid, full_name="No Email")
    service = _service(session)

    with pytest.raises(ValidationError):
        await service.verify_person(person.id)


async def test_check_is_stateless(session):
    service = _service(session)
    outcome = await service.check("jane.doe@stripe.com")
    assert outcome.status == VerificationStatus.VALID


async def test_verify_company_batch(session):
    cid = await _company(session, name="Acme", domain="acme.com")
    await _person(session, cid, full_name="Jane Doe", email="jane.doe@acme.com")
    await _person(session, cid, full_name="Role Acct", email="info@acme.com")
    await _person(session, cid, full_name="No Email")  # skipped
    service = _service(session)

    results = await service.verify_company(cid)
    assert len(results) == 2  # the emailless person is skipped
    statuses = {r.outcome.status for r in results}
    assert VerificationStatus.VALID in statuses
    assert VerificationStatus.RISKY in statuses


async def test_api_check_and_verify_flow(client):
    check = await client.get(
        "/api/v1/email-verification/check", params={"email": "jane.doe@acme.com"}
    )
    assert check.status_code == 200, check.text
    assert check.json()["status"] == "valid"

    created = await client.post(
        "/api/v1/companies", json={"name": "Acme", "domain": "acme.com"}
    )
    cid = created.json()["id"]
    discovered = await client.post(f"/api/v1/companies/{cid}/people/discover")
    pid = discovered.json()["people"][0]["id"]

    resp = await client.post(f"/api/v1/people/{pid}/verify-email")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["outcome"]["status"] in {"valid", "risky", "invalid", "unknown"}

    listed = await client.get(f"/api/v1/people/{pid}/verifications")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_api_verify_company(client):
    created = await client.post(
        "/api/v1/companies", json={"name": "Acme", "domain": "acme.com"}
    )
    cid = created.json()["id"]
    await client.post(f"/api/v1/companies/{cid}/people/discover")

    resp = await client.post(f"/api/v1/companies/{cid}/people/verify-emails")
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)
