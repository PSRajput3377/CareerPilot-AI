"""Cover Letter service (Module 9).

Assembles a generation context from a profile + target company (and optional
job listing), runs a generator, and optionally persists the draft. Generated
letters are drafts: they are stored for review and editing, never auto-sent
(human-in-the-loop gate).
"""

from __future__ import annotations

from datetime import date as _date

from careerpilot.backend.core.exceptions import NotFoundError
from careerpilot.backend.core.logging import get_logger
from careerpilot.backend.models.cover_letter import CoverLetter
from careerpilot.backend.models.user_profile import UserProfile
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.cover_letter import CoverLetterRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.job_match import JobMatchRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.cover_letter import (
    CoverLetterDraft,
    CoverLetterRequest,
)
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.cover_letter.base import (
    CoverLetterContext,
    CoverLetterGenerator,
    get_generator,
)
from careerpilot.backend.services.user_profile import UserProfileService

logger = get_logger("services.cover_letter")


class CoverLetterService:
    """Generate and persist cover letter drafts."""

    def __init__(
        self,
        profile_repo: UserProfileRepository,
        company_repo: CompanyRepository,
        listing_repo: JobListingRepository,
        cover_letter_repo: CoverLetterRepository,
        match_repo: JobMatchRepository,
        generator: CoverLetterGenerator | None = None,
    ) -> None:
        self._profiles = UserProfileService(profile_repo)
        self._companies = CompanyService(company_repo)
        self._listings = listing_repo
        self._letters = cover_letter_repo
        self._matches = match_repo
        self._generator = generator or get_generator()

    async def generate(
        self, profile_id: int, request: CoverLetterRequest
    ) -> tuple[CoverLetterDraft, CoverLetter | None]:
        """Generate a cover letter draft, persisting it unless ``save`` is False.

        Returns the draft and the persisted row (or ``None`` for a preview).
        """
        profile = await self._profiles.get(profile_id)
        company = await self._companies.get(request.company_id)

        role_title: str | None = None
        matched_skills: list[str] = []
        if request.job_listing_id is not None:
            listing = await self._listings.get(request.job_listing_id)
            if listing is None or listing.company_id != company.id:
                raise NotFoundError(
                    f"Job listing {request.job_listing_id} not found for "
                    f"company {company.id}"
                )
            role_title = listing.title
            match = await self._matches.get_for_pair(
                profile_id, request.job_listing_id
            )
            if match and match.matched_skills:
                matched_skills = [
                    s.strip() for s in match.matched_skills.split(",") if s.strip()
                ]

        ctx = CoverLetterContext(
            candidate_name=profile.name,
            company_name=company.name,
            role_title=role_title,
            preferred_role=profile.preferred_role,
            candidate_skills=[s.name for s in profile.skills],
            matched_skills=matched_skills,
            company_industry=company.industry,
            recent_experience=_recent_experience(profile),
            tone=request.tone,
        )

        draft = self._generator.generate(ctx)
        logger.info(
            "Generated cover letter (%s, %d words) for profile id=%s -> company id=%s",
            draft.generator,
            draft.word_count,
            profile_id,
            company.id,
        )

        if not request.save:
            return draft, None

        letter = CoverLetter(
            profile_id=profile_id,
            company_id=company.id,
            job_listing_id=request.job_listing_id,
            subject=draft.subject,
            body=draft.body,
            tone=draft.tone,
            word_count=draft.word_count,
            generator=draft.generator,
        )
        saved = await self._letters.add(letter)
        return draft, saved

    async def get(self, letter_id: int) -> CoverLetter:
        letter = await self._letters.get(letter_id)
        if letter is None:
            raise NotFoundError(f"Cover letter {letter_id} not found")
        return letter

    async def list_for_profile(
        self, profile_id: int, *, limit: int = 100
    ) -> list[CoverLetter]:
        await self._profiles.get(profile_id)  # 404 if missing
        return await self._letters.list_for_profile(profile_id, limit=limit)

    async def delete(self, letter_id: int) -> None:
        letter = await self.get(letter_id)
        await self._letters.delete(letter)
        logger.info("Deleted cover letter id=%s", letter_id)


def _recent_experience(profile: UserProfile) -> str | None:
    """Best-effort 'Title at Company' from the profile's experiences."""
    experiences = list(profile.experiences)
    if not experiences:
        return None
    # Prefer a current role (no end_date), else the latest by start_date.
    current = [e for e in experiences if e.end_date is None]
    pool = current or experiences
    pool.sort(key=lambda e: (e.start_date is None, e.start_date or _MIN_DATE), reverse=True)
    top = pool[0]
    if top.title and top.company:
        return f"{top.title} at {top.company}"
    return top.title or None


_MIN_DATE = _date.min
