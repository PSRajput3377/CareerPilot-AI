"""Service + API tests for Job Matching (Module 8)."""

from __future__ import annotations

from careerpilot.backend.models.job_listing import JobListing
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.job_match import JobMatchRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.company import CompanyCreate
from careerpilot.backend.schemas.user_profile import UserProfileCreate
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.job_matching import JobMatchingService
from careerpilot.backend.services.user_profile import UserProfileService


async def _profile(session, **kw) -> int:
    service = UserProfileService(UserProfileRepository(session))
    payload = UserProfileCreate(
        name=kw.pop("name", "Jane Engineer"),
        email=kw.pop("email", "jane@example.com"),
        preferred_role=kw.pop("preferred_role", "Backend Engineer"),
        preferred_location=kw.pop("preferred_location", "Remote"),
        skills=[{"name": s} for s in kw.pop("skills", ["Python", "FastAPI", "AWS"])],
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
            external_id=kw.pop("external_id", None),
            title=kw.pop("title", "Backend Engineer"),
            description=kw.pop("description", "Python and FastAPI on AWS."),
            location=kw.pop("location", "Remote"),
            remote=kw.pop("remote", True),
        )
    )
    return listing.id


def _service(session) -> JobMatchingService:
    return JobMatchingService(
        UserProfileRepository(session),
        CompanyRepository(session),
        JobListingRepository(session),
        JobMatchRepository(session),
    )


async def test_match_company_ranks_listings(session):
    pid = await _profile(session)
    cid = await _company(session, name="Acme", domain="acme.com")
    await _listing(
        session, cid, title="Backend Engineer", description="Python, FastAPI, AWS."
    )
    await _listing(
        session,
        cid,
        title="Frontend Designer",
        description="Photoshop and Figma skills.",
        remote=False,
        location="Berlin",
    )
    service = _service(session)

    results = await service.match_company(pid, cid)
    assert len(results) == 2
    # Ranked: backend role should outscore the design role.
    assert results[0].title == "Backend Engineer"
    assert results[0].match.score > results[1].match.score
    assert "python" in results[0].match.matched_skills


async def test_match_is_idempotent(session):
    pid = await _profile(session)
    cid = await _company(session, name="Acme")
    await _listing(session, cid, external_id="j1", title="Backend Engineer")
    service = _service(session)

    await service.match_company(pid, cid)
    await service.match_company(pid, cid)  # re-run

    matches = await service.list_matches(pid)
    assert len(matches) == 1  # no duplicate per (profile, listing)


async def test_match_company_with_no_listings_returns_empty(session):
    pid = await _profile(session)
    cid = await _company(session, name="Empty Co")
    service = _service(session)
    assert await service.match_company(pid, cid) == []


async def test_list_matches_scoped_to_company(session):
    pid = await _profile(session)
    cid1 = await _company(session, name="Acme", domain="acme.com")
    cid2 = await _company(session, name="Globex", domain="globex.com")
    await _listing(session, cid1, title="Backend Engineer")
    await _listing(session, cid2, title="Platform Engineer")
    service = _service(session)

    await service.match_company(pid, cid1)
    await service.match_company(pid, cid2)

    only_acme = await service.list_matches(pid, cid1)
    assert len(only_acme) == 1
    all_matches = await service.list_matches(pid)
    assert len(all_matches) == 2


async def test_match_single_listing(session):
    pid = await _profile(session)
    cid = await _company(session, name="Acme")
    jid = await _listing(session, cid, title="Backend Engineer")
    service = _service(session)

    result = await service.match_listing(pid, jid)
    assert result.job_listing_id == jid
    assert result.match.score > 0


async def test_api_match_and_list(client):
    # Create profile.
    prof = await client.post(
        "/api/v1/profiles",
        json={
            "name": "Jane Engineer",
            "email": "jane@example.com",
            "preferred_role": "Backend Engineer",
            "preferred_location": "Remote",
            "skills": [{"name": "Python"}, {"name": "FastAPI"}],
        },
    )
    pid = prof.json()["id"]

    # Create company + a job listing (via career-page detection fixture path is
    # offline; here we use the company create + detect to ensure listings exist
    # is unnecessary — match endpoint handles empty gracefully). Create company:
    comp = await client.post(
        "/api/v1/companies", json={"name": "Acme", "domain": "acme.com"}
    )
    cid = comp.json()["id"]

    # No listings yet → empty ranked result.
    empty = await client.post(f"/api/v1/profiles/{pid}/match/companies/{cid}")
    assert empty.status_code == 200, empty.text
    assert empty.json() == []

    # Listing matches endpoint returns a list.
    listed = await client.get(f"/api/v1/profiles/{pid}/matches")
    assert listed.status_code == 200
    assert listed.json() == []


async def test_api_match_missing_profile_404(client):
    comp = await client.post("/api/v1/companies", json={"name": "Acme"})
    cid = comp.json()["id"]
    resp = await client.post(f"/api/v1/profiles/999999/match/companies/{cid}")
    assert resp.status_code == 404
