"""Subject service (Module 11).

Resolves a context (candidate, company, recipient, role) from stored rows and
runs a generator to produce ranked subject lines. Stateless — subjects are
generated on demand and not persisted; the chosen line is consumed when an
outreach message is drafted (Module 14) and sent (Module 15).
"""

from __future__ import annotations

from careerpilot.backend.core.exceptions import NotFoundError
from careerpilot.backend.core.logging import get_logger
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.person import PersonRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.subject import SubjectRequest, SubjectResult
from careerpilot.backend.services.subject.base import (
    SubjectContext,
    SubjectGenerator,
    get_generator,
)

logger = get_logger("services.subject")


class SubjectService:
    """Generate ranked subject lines from stored context."""

    def __init__(
        self,
        profile_repo: UserProfileRepository,
        company_repo: CompanyRepository,
        person_repo: PersonRepository,
        listing_repo: JobListingRepository,
        generator: SubjectGenerator | None = None,
    ) -> None:
        self._profiles = profile_repo
        self._companies = company_repo
        self._people = person_repo
        self._listings = listing_repo
        self._generator = generator or get_generator()

    async def generate(self, request: SubjectRequest) -> SubjectResult:
        """Resolve the context and produce ranked subject lines."""
        profile = await self._profiles.get(request.profile_id)
        if profile is None:
            raise NotFoundError(f"User profile {request.profile_id} not found")

        company_name: str | None = None
        if request.company_id is not None:
            company = await self._companies.get(request.company_id)
            if company is None:
                raise NotFoundError(f"Company {request.company_id} not found")
            company_name = company.name

        recipient_first: str | None = None
        if request.person_id is not None:
            person = await self._people.get(request.person_id)
            if person is None:
                raise NotFoundError(f"Person {request.person_id} not found")
            recipient_first = _first_name(person.full_name)

        role: str | None = profile.preferred_role
        if request.job_listing_id is not None:
            listing = await self._listings.get(request.job_listing_id)
            if listing is None:
                raise NotFoundError(f"Job listing {request.job_listing_id} not found")
            role = listing.title

        ctx = SubjectContext(
            candidate_name=profile.name,
            candidate_first_name=_first_name(profile.name) or profile.name,
            company_name=company_name,
            role=role,
            recipient_first_name=recipient_first,
            limit=request.limit,
        )
        result = self._generator.generate(ctx)
        logger.info(
            "Generated %d subject(s) via '%s' for profile id=%s",
            len(result.candidates),
            result.generator,
            request.profile_id,
        )
        return result


def _first_name(full_name: str) -> str | None:
    parts = [p for p in (full_name or "").split() if p]
    return parts[0] if parts else None
