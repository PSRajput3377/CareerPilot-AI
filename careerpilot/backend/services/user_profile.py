"""Service layer for User Profile (Module 1).

Holds business rules and orchestrates the repository. The API and CLI both call
into this layer, keeping behaviour consistent across entrypoints.
"""

from __future__ import annotations

from careerpilot.backend.core.exceptions import ConflictError, NotFoundError
from careerpilot.backend.core.logging import get_logger
from careerpilot.backend.models.user_profile import (
    Education,
    Experience,
    Skill,
    UserProfile,
)
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.user_profile import (
    UserProfileCreate,
    UserProfileUpdate,
)

logger = get_logger("services.user_profile")


class UserProfileService:
    """Business operations for user profiles."""

    def __init__(self, repository: UserProfileRepository) -> None:
        self._repo = repository

    async def create(self, payload: UserProfileCreate) -> UserProfile:
        """Create a profile with nested skills/experience/education.

        Raises :class:`ConflictError` if the email is already registered.
        """
        existing = await self._repo.get_by_email(str(payload.email))
        if existing is not None:
            raise ConflictError(f"A profile with email '{payload.email}' already exists")

        profile = UserProfile(
            name=payload.name,
            email=str(payload.email),
            phone=payload.phone,
            resume_path=payload.resume_path,
            github_url=_url(payload.github_url),
            portfolio_url=_url(payload.portfolio_url),
            linkedin_url=_url(payload.linkedin_url),
            preferred_role=payload.preferred_role,
            preferred_location=payload.preferred_location,
            work_authorization=payload.work_authorization,
            preferred_companies=_join_companies(payload.preferred_companies),
            preferred_salary_min=payload.preferred_salary_min,
            preferred_salary_max=payload.preferred_salary_max,
            availability=payload.availability,
        )
        profile.skills = [
            Skill(name=s.name, proficiency=s.proficiency, years=s.years)
            for s in _dedupe_skills(payload.skills)
        ]
        profile.experiences = [
            Experience(
                company=e.company,
                title=e.title,
                location=e.location,
                start_date=e.start_date,
                end_date=e.end_date,
                description=e.description,
            )
            for e in payload.experiences
        ]
        profile.educations = [
            Education(
                institution=ed.institution,
                degree=ed.degree,
                field_of_study=ed.field_of_study,
                start_date=ed.start_date,
                end_date=ed.end_date,
                grade=ed.grade,
            )
            for ed in payload.educations
        ]

        created = await self._repo.add(profile)
        logger.info("Created user profile id=%s email=%s", created.id, created.email)
        return created

    async def get(self, profile_id: int) -> UserProfile:
        """Fetch a profile or raise :class:`NotFoundError`."""
        profile = await self._repo.get(profile_id)
        if profile is None:
            raise NotFoundError(f"User profile {profile_id} not found")
        return profile

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[UserProfile]:
        return await self._repo.list(limit=limit, offset=offset)

    async def save(self, profile: UserProfile) -> UserProfile:
        """Persist mutations made to a managed profile instance.

        Used by collaborating services (e.g. the resume parser) that mutate a
        profile's children and need to flush within the same transaction.
        """
        return await self._repo.add(profile)

    async def update(self, profile_id: int, payload: UserProfileUpdate) -> UserProfile:
        """Apply a partial update to scalar profile fields."""
        profile = await self.get(profile_id)
        data = payload.model_dump(exclude_unset=True)

        if "preferred_companies" in data and data["preferred_companies"] is not None:
            data["preferred_companies"] = _join_companies(data["preferred_companies"])
        for url_field in ("github_url", "portfolio_url", "linkedin_url"):
            if url_field in data and data[url_field] is not None:
                data[url_field] = str(data[url_field])

        for field, value in data.items():
            setattr(profile, field, value)

        updated = await self._repo.add(profile)
        logger.info("Updated user profile id=%s", updated.id)
        return updated

    async def delete(self, profile_id: int) -> None:
        """Delete a profile and its children (cascade)."""
        profile = await self.get(profile_id)
        await self._repo.delete(profile)
        logger.info("Deleted user profile id=%s", profile_id)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _url(value: object) -> str | None:
    return str(value) if value is not None else None


def _join_companies(companies: list[str]) -> str:
    return ", ".join(c.strip() for c in companies if c and c.strip())


def _dedupe_skills(skills):
    """Drop duplicate skill names (case-insensitive), keeping first occurrence."""
    seen: set[str] = set()
    out = []
    for skill in skills:
        key = skill.name.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(skill)
    return out
