"""Email Verification service (Module 7).

The ``verify deliverability`` gate of the outreach pipeline. For a stored person
with an email, run a verifier, persist the verdict (idempotent on
(person, email)), and set ``person.email_verified`` true only when the verdict
is ``VALID``. Nothing downstream may send to a person who has not passed here.
"""

from __future__ import annotations

from careerpilot.backend.core.exceptions import ValidationError
from careerpilot.backend.core.logging import get_logger
from careerpilot.backend.models.email_verification import (
    EmailVerification,
    VerificationStatus,
)
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.email_verification import (
    EmailVerificationRepository,
)
from careerpilot.backend.repositories.person import PersonRepository
from careerpilot.backend.schemas.email_verification import (
    PersonVerificationResult,
    VerificationOutcome,
)
from careerpilot.backend.services.email_verification.base import (
    EmailVerifier,
    get_verifier,
)
from careerpilot.backend.services.people import PeopleService

logger = get_logger("services.email_verification")


class EmailVerificationService:
    """Verify people's emails and persist the verdicts."""

    def __init__(
        self,
        company_repo: CompanyRepository,
        person_repo: PersonRepository,
        verification_repo: EmailVerificationRepository,
        verifier: EmailVerifier | None = None,
    ) -> None:
        self._people = PeopleService(company_repo, person_repo)
        self._person_repo = person_repo
        self._verifications = verification_repo
        self._verifier = verifier or get_verifier()

    async def check(self, email: str) -> VerificationOutcome:
        """Verify an arbitrary address without persisting (stateless)."""
        return await self._verifier.verify(email)

    async def verify_person(self, person_id: int) -> PersonVerificationResult:
        """Verify a stored person's email, persist the verdict, set the flag."""
        person = await self._people.get(person_id)
        if not person.email:
            raise ValidationError(f"Person {person_id} has no email to verify")

        outcome = await self._verifier.verify(person.email)
        await self._upsert(person_id, outcome)

        verified = outcome.status == VerificationStatus.VALID
        # Only ever flip true on a VALID verdict; never auto-clear a prior pass
        # for the same address (a transient re-check shouldn't revoke it).
        if verified and not person.email_verified:
            person.email_verified = True
            await self._person_repo.add(person)
        logger.info(
            "Verified person id=%s email=%s -> %s (conf=%.2f)",
            person_id,
            outcome.email,
            outcome.status.value,
            outcome.confidence,
        )
        return PersonVerificationResult(
            person_id=person_id,
            outcome=outcome,
            email_verified=person.email_verified,
        )

    async def verify_company(self, company_id: int) -> list[PersonVerificationResult]:
        """Verify every person at a company who has an email."""
        people = await self._people.list_for_company(company_id)
        results: list[PersonVerificationResult] = []
        for person in people:
            if not person.email:
                continue
            results.append(await self.verify_person(person.id))
        valid = sum(
            1 for r in results if r.outcome.status == VerificationStatus.VALID
        )
        logger.info(
            "Verification pass for company id=%s: %d/%d valid",
            company_id,
            valid,
            len(results),
        )
        return results

    async def list_for_person(self, person_id: int) -> list[EmailVerification]:
        """Return stored verification records for a person (404 if missing)."""
        await self._people.get(person_id)  # 404 if missing
        return await self._verifications.list_for_person(person_id)

    # -- internals --------------------------------------------------------- #

    async def _upsert(
        self, person_id: int, outcome: VerificationOutcome
    ) -> EmailVerification:
        existing = await self._verifications.get_for_person_email(
            person_id, outcome.email
        )
        if existing is None:
            return await self._verifications.add(_to_model(person_id, outcome))
        existing.status = outcome.status
        existing.syntax_ok = outcome.syntax_ok
        existing.domain_ok = outcome.domain_ok
        existing.mx_found = outcome.mx_found
        existing.is_disposable = outcome.is_disposable
        existing.is_role_account = outcome.is_role_account
        existing.confidence = outcome.confidence
        existing.reason = outcome.reason
        existing.verifier = outcome.verifier
        return await self._verifications.add(existing)


def _to_model(person_id: int, outcome: VerificationOutcome) -> EmailVerification:
    return EmailVerification(
        person_id=person_id,
        email=outcome.email,
        status=outcome.status,
        syntax_ok=outcome.syntax_ok,
        domain_ok=outcome.domain_ok,
        mx_found=outcome.mx_found,
        is_disposable=outcome.is_disposable,
        is_role_account=outcome.is_role_account,
        confidence=outcome.confidence,
        reason=outcome.reason,
        verifier=outcome.verifier,
    )
