"""Service + API tests for resume parsing and profile merge (Module 2)."""

from __future__ import annotations

from pathlib import Path

from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.user_profile import UserProfileCreate
from careerpilot.backend.services.resume import ResumeService
from careerpilot.backend.services.user_profile import UserProfileService

SAMPLE = Path(__file__).parent / "sample_resume.txt"


async def test_parse_into_profile_merges_sections(session):
    profiles = UserProfileService(UserProfileRepository(session))
    profile = await profiles.create(
        UserProfileCreate(
            name="Jane", email="jane@example.com", skills=[{"name": "Python"}]
        )
    )

    resume = ResumeService(profiles)
    result = await resume.parse_file_into_profile(SAMPLE, profile.id)

    assert result.applied is True
    refreshed = await profiles.get(profile.id)
    skill_names = {s.name for s in refreshed.skills}
    # Pre-existing "Python" not duplicated; new skills unioned in.
    assert sum(1 for s in refreshed.skills if s.name.lower() == "python") == 1
    assert "Kubernetes" in skill_names
    assert len(refreshed.experiences) >= 2
    assert len(refreshed.projects) >= 1
    assert len(refreshed.achievements) == 2
    # Contact link backfilled from resume.
    assert refreshed.github_url == "https://github.com/janeqeng"


async def test_api_parse_resume_upload(client):
    content = SAMPLE.read_bytes()
    resp = await client.post(
        "/api/v1/resumes/parse",
        files={"file": ("resume.txt", content, "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["parser"] == "heuristic"
    assert any(s["name"] == "Python" for s in body["skills"])


async def test_api_parse_into_profile(client):
    created = await client.post(
        "/api/v1/profiles", json={"name": "Jane", "email": "jane2@example.com"}
    )
    pid = created.json()["id"]

    content = SAMPLE.read_bytes()
    resp = await client.post(
        f"/api/v1/resumes/parse-into-profile?profile_id={pid}",
        files={"file": ("resume.txt", content, "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["applied"] is True

    got = await client.get(f"/api/v1/profiles/{pid}")
    profile = got.json()
    assert len(profile["projects"]) >= 1
    assert len(profile["achievements"]) == 2
