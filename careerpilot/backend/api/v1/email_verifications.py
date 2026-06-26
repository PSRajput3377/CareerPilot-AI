"""Email Verification API routes (Module 7).

A stateless ``/check`` endpoint verifies an arbitrary address; the person- and
company-scoped endpoints verify stored people, persist the verdict, and set
``email_verified`` on a ``valid`` result.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from careerpilot.backend.api.dependencies import EmailVerificationServiceDep
from careerpilot.backend.schemas.email_verification import (
    EmailVerificationRead,
    PersonVerificationResult,
    VerificationOutcome,
)

router = APIRouter(tags=["email-verification"])


@router.get("/email-verification/check", response_model=VerificationOutcome)
async def check_email(
    service: EmailVerificationServiceDep,
    email: str = Query(..., min_length=1, description="Address to verify"),
) -> VerificationOutcome:
    """Verify an arbitrary email without persisting anything."""
    return await service.check(email)


@router.post("/people/{person_id}/verify-email", response_model=PersonVerificationResult)
async def verify_person_email(
    person_id: int, service: EmailVerificationServiceDep
) -> PersonVerificationResult:
    """Verify a stored person's email and persist the verdict."""
    return await service.verify_person(person_id)


@router.get(
    "/people/{person_id}/verifications",
    response_model=list[EmailVerificationRead],
)
async def list_person_verifications(
    person_id: int, service: EmailVerificationServiceDep
) -> list[EmailVerificationRead]:
    """List stored verification records for a person."""
    records = await service.list_for_person(person_id)
    return [EmailVerificationRead.model_validate(r) for r in records]


@router.post(
    "/companies/{company_id}/people/verify-emails",
    response_model=list[PersonVerificationResult],
)
async def verify_company_emails(
    company_id: int, service: EmailVerificationServiceDep
) -> list[PersonVerificationResult]:
    """Verify every person at a company who has an email."""
    return await service.verify_company(company_id)
