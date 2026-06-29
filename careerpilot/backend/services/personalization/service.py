"""Personalization service (Module 12).

The orchestrator that ties the platform together: it resolves a profile, a
recipient, the target company/role, the candidate's overlapping skills (from a
job match), an optional base template, and the best subject line into one
personalized outreach draft.

Stateless and read-only: it composes a reviewable draft. Persisting it as a
reviewable, sendable message is Module 14's job; sending is Module 15's. Nothing
here ever sends.
"""

from __future__ import annotations

from careerpilot.backend.core.exceptions import NotFoundError
from careerpilot.backend.core.logging import get_logger
from careerpilot.backend.models.user_profile import UserProfile
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.email_template import EmailTemplateRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.job_match import JobMatchRepository
from careerpilot.backend.repositories.person import PersonRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.email_template import RenderContext
from careerpilot.backend.schemas.personalization import (
    PersonalizationRequest,
    PersonalizedEmail,
)
from careerpilot.backend.schemas.subject import SubjectRequest
from careerpilot.backend.services.personalization.base import (
    PersonalizationContext,
    PersonalizationEngine,
    get_engine,
)
from careerpilot.backend.services.subject import SubjectService
from careerpilot.backend.services.templating import EmailTemplateService

logger = get_logger("services.personalization")


class PersonalizationService:
    """Compose personalized outreach drafts from stored context."""

    def __init__(
        self,
        profile_repo: UserProfileRepository,
        company_repo: CompanyRepository,
        person_repo: PersonRepository,
        listing_repo: JobListingRepository,
        match_repo: JobMatchRepository,
        template_repo: EmailTemplateRepository,
        subject_service: SubjectService,
        template_service: EmailTemplateService,
        engine: PersonalizationEngine | None = None,
    ) -> None:
        self._profiles = profile_repo
        self._companies = company_repo
        self._people = person_repo
        self._listings = listing_repo
        self._matches = match_repo
        self._templates = template_repo
        self._subjects = subject_service
        self._template_service = template_service
        self._engine = engine or get_engine()

    async def personalize(
        self, request: PersonalizationRequest
    ) -> PersonalizedEmail:
        """Resolve the full context and compose a personalized draft."""
        profile = await self._profiles.get(request.profile_id)
        if profile is None:
            raise NotFoundError(f"User profile {request.profile_id} not found")

        person = await self._people.get(request.person_id)
        if person is None:
            raise NotFoundError(f"Person {request.person_id} not found")

        # A person always belongs to a company; default the target to it.
        company_id = request.company_id or person.company_id
        company = await self._companies.get(company_id)
        if company is None:
            raise NotFoundError(f"Company {company_id} not found")

        role: str | None = profile.preferred_role
        if request.job_listing_id is not None:
            listing = await self._listings.get(request.job_listing_id)
            if listing is None:
                raise NotFoundError(
                    f"Job listing {request.job_listing_id} not found"
                )
            role = listing.title

        matched_skills = await self._matched_skills(
            request.profile_id, request.job_listing_id
        )

        # Best subject for this context.
        subject_result = await self._subjects.generate(
            SubjectRequest(
                profile_id=request.profile_id,
                company_id=company_id,
                person_id=request.person_id,
                job_listing_id=request.job_listing_id,
                limit=1,
            )
        )
        subject = subject_result.best.text if subject_result.best else ""

        # Optional base template body.
        base_body = ""
        missing: list[str] = []
        if request.template_id is not None:
            rendered = await self._template_service.render(
                request.template_id,
                RenderContext(
                    profile_id=request.profile_id,
                    company_id=company_id,
                    person_id=request.person_id,
                    job_listing_id=request.job_listing_id,
                ),
            )
            base_body = rendered.body
            missing = rendered.missing_placeholders
            if not subject:
                subject = rendered.subject

        ctx = PersonalizationContext(
            candidate_name=profile.name,
            candidate_first_name=_first(profile.name) or profile.name,
            recipient_name=person.full_name,
            recipient_first_name=_first(person.full_name) or person.full_name,
            candidate_role=profile.preferred_role,
            company_name=company.name,
            company_industry=company.industry,
            role=role,
            matched_skills=matched_skills,
            candidate_skills=[s.name for s in profile.skills],
            recent_experience=_recent_experience(profile),
            subject=subject,
            base_body=base_body,
            missing_placeholders=missing,
            tone=request.tone,
        )

        draft = self._engine.compose(ctx)
        logger.info(
            "Personalized draft (engine=%s, score=%.2f, %d words) profile id=%s -> "
            "person id=%s",
            draft.engine,
            draft.personalization_score,
            draft.word_count,
            request.profile_id,
            request.person_id,
        )
        return draft

    async def _matched_skills(
        self, profile_id: int, job_listing_id: int | None
    ) -> list[str]:
        if job_listing_id is None:
            return []
        match = await self._matches.get_for_pair(profile_id, job_listing_id)
        if match is None or not match.matched_skills:
            return []
        return [s.strip() for s in match.matched_skills.split(",") if s.strip()]


def _first(full_name: str) -> str | None:
    parts = [p for p in (full_name or "").split() if p]
    return parts[0] if parts else None


def _recent_experience(profile: UserProfile) -> str | None:
    """Best-effort 'Title at Company' from the profile's experiences."""
    from datetime import date

    experiences = list(profile.experiences)
    if not experiences:
        return None
    current = [e for e in experiences if e.end_date is None]
    pool = current or experiences
    pool.sort(
        key=lambda e: (e.start_date is None, e.start_date or date.min), reverse=True
    )
    top = pool[0]
    if top.title and top.company:
        return f"a {top.title} at {top.company}"
    return top.title or None
