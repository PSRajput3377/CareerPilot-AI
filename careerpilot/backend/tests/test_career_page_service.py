"""Service + API tests for Career Page Detection (Module 4)."""

from __future__ import annotations

from careerpilot.backend.models.job_listing import ATSPlatform
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.schemas.company import CompanyCreate
from careerpilot.backend.schemas.job_listing import JobListingCreate
from careerpilot.backend.services.career_page import CareerPageService
from careerpilot.backend.services.career_page.pattern import PatternCareerPageDetector
from careerpilot.backend.services.company import CompanyService


async def _make_company(session, **kw) -> int:
    service = CompanyService(CompanyRepository(session))
    company = await service.create(CompanyCreate(name=kw.pop("name", "Acme"), **kw))
    return company.id


def _service(session, fixture=None) -> CareerPageService:
    detector = PatternCareerPageDetector(listings_fixture=fixture)
    return CareerPageService(
        CompanyRepository(session), JobListingRepository(session), detector=detector
    )


async def test_detect_updates_company_and_saves_listings(session):
    cid = await _make_company(
        session, name="Acme", career_page="https://boards.greenhouse.io/acme"
    )
    fixture = {
        "Acme": [
            JobListingCreate(external_id="1", title="Backend Engineer", remote=True),
            JobListingCreate(external_id="2", title="SRE"),
        ]
    }
    service = _service(session, fixture)
    result = await service.detect_for_company(cid)

    assert result.detection.platform == ATSPlatform.GREENHOUSE
    assert result.listings_saved == 2

    company = await CompanyService(CompanyRepository(session)).get(cid)
    assert company.ats_platform == "greenhouse"
    assert company.hiring_platform == "greenhouse"

    jobs = await service.list_jobs(cid)
    assert {j.title for j in jobs} == {"Backend Engineer", "SRE"}


async def test_detect_is_idempotent_on_listings(session):
    cid = await _make_company(session, name="Acme", hiring_platform="lever")
    fixture = {"lever": [JobListingCreate(external_id="42", title="Engineer")]}
    service = _service(session, fixture)

    await service.detect_for_company(cid)
    await service.detect_for_company(cid)  # run again

    jobs = await service.list_jobs(cid)
    assert len(jobs) == 1  # no duplicate for external_id=42


async def test_api_detect_and_list_jobs(client):
    created = await client.post(
        "/api/v1/companies", json={"name": "Acme", "hiring_platform": "greenhouse"}
    )
    cid = created.json()["id"]

    resp = await client.post(f"/api/v1/companies/{cid}/detect-career-page")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["detection"]["platform"] == "greenhouse"

    jobs = await client.get(f"/api/v1/companies/{cid}/jobs")
    assert jobs.status_code == 200
    assert isinstance(jobs.json(), list)


async def test_api_detect_missing_company_404(client):
    resp = await client.post("/api/v1/companies/999999/detect-career-page")
    assert resp.status_code == 404
