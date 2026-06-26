"""Service-layer tests for User Profile (Module 1)."""

from __future__ import annotations

import pytest

from careerpilot.backend.core.exceptions import ConflictError, NotFoundError
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.user_profile import (
    UserProfileCreate,
    UserProfileUpdate,
)
from careerpilot.backend.services.user_profile import UserProfileService


def _service(session) -> UserProfileService:
    return UserProfileService(UserProfileRepository(session))


def _sample_payload(**overrides) -> UserProfileCreate:
    data = {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "preferred_role": "Backend Engineer",
        "preferred_companies": ["Stripe", "Datadog"],
        "skills": [{"name": "Python"}, {"name": "python"}, {"name": "Go"}],
        "experiences": [
            {"company": "Analytical Engines", "title": "Engineer"},
        ],
        "educations": [{"institution": "Cambridge"}],
    }
    data.update(overrides)
    return UserProfileCreate(**data)


async def test_create_profile_persists_nested_and_dedupes_skills(session):
    service = _service(session)
    profile = await service.create(_sample_payload())

    assert profile.id is not None
    # "Python" and "python" collapse to one.
    assert {s.name for s in profile.skills} == {"Python", "Go"}
    assert len(profile.experiences) == 1
    assert len(profile.educations) == 1
    # Companies stored as comma-separated string.
    assert profile.preferred_companies == "Stripe, Datadog"


async def test_create_duplicate_email_raises_conflict(session):
    service = _service(session)
    await service.create(_sample_payload())
    with pytest.raises(ConflictError):
        await service.create(_sample_payload(name="Clone"))


async def test_get_missing_raises_not_found(session):
    service = _service(session)
    with pytest.raises(NotFoundError):
        await service.get(99999)


async def test_update_applies_partial_changes(session):
    service = _service(session)
    profile = await service.create(_sample_payload())

    updated = await service.update(
        profile.id,
        UserProfileUpdate(preferred_role="Staff Engineer", preferred_companies=["Vercel"]),
    )
    assert updated.preferred_role == "Staff Engineer"
    assert updated.preferred_companies == "Vercel"
    # Untouched field preserved.
    assert updated.name == "Ada Lovelace"


async def test_delete_removes_profile(session):
    service = _service(session)
    profile = await service.create(_sample_payload())
    await service.delete(profile.id)
    with pytest.raises(NotFoundError):
        await service.get(profile.id)
