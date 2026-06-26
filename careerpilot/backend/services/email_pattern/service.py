"""Email Pattern service (Module 6).

Bridges the deterministic :class:`EmailPatternGenerator` to stored data: for a
person who has no email, generate ranked candidates from the company domain and
write the best guess onto the person — marked ``email_source = pattern`` and
left **unverified** (verification is Module 7).

Honors the verified-email-first invariant: an existing public/verified email is
never overwritten by a guess. Callers can force a refresh of an existing *guess*
with ``overwrite=True``.
"""

from __future__ import annotations

from careerpilot.backend.core.logging import get_logger
from careerpilot.backend.models.person import EmailSource, Person
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.person import PersonRepository
from careerpilot.backend.schemas.email_pattern import (
    EmailPatternResult,
    PersonEmailGuessResult,
)
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.email_pattern.generator import EmailPatternGenerator
from careerpilot.backend.services.people import PeopleService

logger = get_logger("services.email_pattern")


class EmailPatternService:
    """Generate and persist pattern-based email guesses for people."""

    def __init__(
        self,
        company_repo: CompanyRepository,
        person_repo: PersonRepository,
        generator: EmailPatternGenerator | None = None,
    ) -> None:
        self._companies = CompanyService(company_repo)
        self._people = PeopleService(company_repo, person_repo)
        self._person_repo = person_repo
        self._generator = generator or EmailPatternGenerator()

    def preview(self, full_name: str, domain: str) -> EmailPatternResult:
        """Generate candidate emails without touching the database."""
        return self._generator.generate(full_name, domain)

    async def guess_for_person(
        self, person_id: int, *, overwrite: bool = False
    ) -> PersonEmailGuessResult:
        """Fill a stored person's email with the best pattern guess.

        Skips people who already have a public/verified email (or any email when
        ``overwrite`` is False). Returns the candidates either way so callers can
        inspect alternatives.
        """
        person = await self._people.get(person_id)
        company = await self._companies.get(person.company_id)
        domain = company.domain or _domain_from_website(company.website)

        result = self._generator.generate(person.full_name, domain or "")
        candidates = result.candidates

        if not self._should_fill(person, overwrite):
            return PersonEmailGuessResult(
                person_id=person_id,
                filled=False,
                email=person.email,
                candidates=candidates,
            )

        best = result.best
        if best is None:
            return PersonEmailGuessResult(
                person_id=person_id,
                filled=False,
                email=person.email,
                candidates=candidates,
            )

        person.email = best.email
        person.email_source = EmailSource.PATTERN
        person.email_verified = False  # a guess is never verified
        await self._person_repo.add(person)
        logger.info(
            "Filled pattern email for person id=%s (%s) via %s",
            person_id,
            best.email,
            best.pattern,
        )
        return PersonEmailGuessResult(
            person_id=person_id,
            filled=True,
            email=best.email,
            candidates=candidates,
        )

    async def guess_for_company(
        self, company_id: int, *, overwrite: bool = False
    ) -> list[PersonEmailGuessResult]:
        """Fill pattern emails for every eligible person at a company."""
        people = await self._people.list_for_company(company_id)
        if not people:
            return []
        results: list[PersonEmailGuessResult] = []
        for person in people:
            results.append(await self.guess_for_person(person.id, overwrite=overwrite))
        filled = sum(1 for r in results if r.filled)
        logger.info(
            "Pattern-email pass for company id=%s: %d/%d people filled",
            company_id,
            filled,
            len(results),
        )
        return results

    # -- internals --------------------------------------------------------- #

    def _should_fill(self, person: Person, overwrite: bool) -> bool:
        # Never clobber a trustworthy address.
        if person.email and (
            person.email_verified or person.email_source == EmailSource.PUBLIC
        ):
            return False
        if person.email and not overwrite:
            return False
        return True


def _domain_from_website(website: str | None) -> str | None:
    if not website:
        return None
    import re

    host = re.sub(r"^https?://", "", website.strip().lower()).split("/")[0]
    host = re.sub(r"^www\.", "", host)
    return host or None
