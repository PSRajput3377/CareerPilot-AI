"""Job Matching service (Module 8).

Orchestrates: load a profile + a company's job listings → score each pair with a
matcher → upsert the scores (idempotent on (profile, listing)) → return them
ranked. Matching prioritizes which roles to pursue and feeds personalization
downstream.
"""

from __future__ import annotations

from careerpilot.backend.core.exceptions import NotFoundError
from careerpilot.backend.core.logging import get_logger
from careerpilot.backend.models.job_listing import JobListing
from careerpilot.backend.models.job_match import JobMatch
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.job_match import JobMatchRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.job_match import JobMatchResult, MatchScore
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.job_matching.base import (
    JobLike,
    JobMatcher,
    ProfileLike,
    get_matcher,
)
from careerpilot.backend.services.user_profile import UserProfileService

logger = get_logger("services.job_matching")


class JobMatchingService:
    """Score and persist profile↔job fit, ranked for outreach prioritization."""

    def __init__(
        self,
        profile_repo: UserProfileRepository,
        company_repo: CompanyRepository,
        listing_repo: JobListingRepository,
        match_repo: JobMatchRepository,
        matcher: JobMatcher | None = None,
    ) -> None:
        self._profiles = UserProfileService(profile_repo)
        self._companies = CompanyService(company_repo)
        self._listings = listing_repo
        self._matches = match_repo
        self._matcher = matcher or get_matcher()

    @property
    def matcher_name(self) -> str:
        return self._matcher.name

    async def match_company(
        self, profile_id: int, company_id: int
    ) -> list[JobMatchResult]:
        """Score a profile against every job listing at a company, ranked desc."""
        profile = await self._profiles.get(profile_id)
        await self._companies.get(company_id)  # 404 if missing
        listings = await self._listings.list_for_company(company_id)
        if not listings:
            return []

        profile_view = _profile_view(profile)
        results: list[JobMatchResult] = []
        for listing in listings:
            score = self._matcher.match(profile_view, _job_view(listing))
            match = await self._upsert(profile_id, listing.id, score)
            results.append(_to_result(listing, match))

        results.sort(key=lambda r: r.match.score, reverse=True)
        logger.info(
            "Matched profile id=%s against %d listings at company id=%s via '%s'",
            profile_id,
            len(listings),
            company_id,
            self._matcher.name,
        )
        return results

    async def match_listing(
        self, profile_id: int, job_listing_id: int
    ) -> JobMatchResult:
        """Score a profile against a single job listing."""
        profile = await self._profiles.get(profile_id)
        listing = await self._listings.get(job_listing_id)
        if listing is None:
            raise NotFoundError(f"Job listing {job_listing_id} not found")

        score = self._matcher.match(_profile_view(profile), _job_view(listing))
        match = await self._upsert(profile_id, job_listing_id, score)
        return _to_result(listing, match)

    async def list_matches(
        self, profile_id: int, company_id: int | None = None, *, limit: int = 100
    ) -> list[JobMatch]:
        """Return stored matches for a profile (optionally one company), ranked."""
        await self._profiles.get(profile_id)  # 404 if missing
        if company_id is not None:
            return await self._matches.list_for_profile_company(
                profile_id, company_id, limit=limit
            )
        return await self._matches.list_for_profile(profile_id, limit=limit)

    # -- internals --------------------------------------------------------- #

    async def _upsert(
        self, profile_id: int, job_listing_id: int, score: MatchScore
    ) -> JobMatch:
        existing = await self._matches.get_for_pair(profile_id, job_listing_id)
        if existing is None:
            return await self._matches.add(
                _to_model(profile_id, job_listing_id, score)
            )
        existing.score = score.score
        existing.skill_score = score.skill_score
        existing.title_score = score.title_score
        existing.location_score = score.location_score
        existing.matched_skills = _join(score.matched_skills)
        existing.missing_skills = _join(score.missing_skills)
        existing.rationale = score.rationale
        existing.matcher = score.matcher
        return await self._matches.add(existing)


def _profile_view(profile) -> ProfileLike:
    return ProfileLike(
        skills=[s.name for s in profile.skills],
        preferred_role=profile.preferred_role,
        preferred_location=profile.preferred_location,
    )


def _job_view(listing: JobListing) -> JobLike:
    return JobLike(
        title=listing.title,
        description=listing.description,
        location=listing.location,
        remote=listing.remote,
    )


def _to_model(profile_id: int, job_listing_id: int, score: MatchScore) -> JobMatch:
    return JobMatch(
        profile_id=profile_id,
        job_listing_id=job_listing_id,
        score=score.score,
        skill_score=score.skill_score,
        title_score=score.title_score,
        location_score=score.location_score,
        matched_skills=_join(score.matched_skills),
        missing_skills=_join(score.missing_skills),
        rationale=score.rationale,
        matcher=score.matcher,
    )


def _to_result(listing: JobListing, match: JobMatch) -> JobMatchResult:
    from careerpilot.backend.schemas.job_match import JobMatchRead

    return JobMatchResult(
        job_listing_id=listing.id,
        title=listing.title,
        company_id=listing.company_id,
        match=JobMatchRead.model_validate(match),
    )


def _join(items: list[str]) -> str:
    return ", ".join(s.strip() for s in items if s and s.strip())
