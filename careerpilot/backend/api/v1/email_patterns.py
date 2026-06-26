"""Email Pattern Generator API routes (Module 6).

A stateless ``/preview`` endpoint generates candidate emails from a name +
domain; the company- and person-scoped endpoints fill stored people's missing
emails with the best guess (left unverified, per the outreach contract).
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from careerpilot.backend.api.dependencies import EmailPatternServiceDep
from careerpilot.backend.schemas.email_pattern import (
    EmailPatternResult,
    PersonEmailGuessResult,
)

router = APIRouter(tags=["email-patterns"])


@router.get("/email-patterns/preview", response_model=EmailPatternResult)
async def preview_email_patterns(
    service: EmailPatternServiceDep,
    full_name: str = Query(..., min_length=1, description="Person's full name"),
    domain: str = Query(..., min_length=1, description="Company domain"),
) -> EmailPatternResult:
    """Generate ranked candidate emails without persisting anything."""
    return service.preview(full_name, domain)


@router.post("/people/{person_id}/guess-email", response_model=PersonEmailGuessResult)
async def guess_person_email(
    person_id: int,
    service: EmailPatternServiceDep,
    overwrite: bool = Query(False, description="Replace an existing guess email"),
) -> PersonEmailGuessResult:
    """Fill a stored person's missing email with the best pattern guess."""
    return await service.guess_for_person(person_id, overwrite=overwrite)


@router.post(
    "/companies/{company_id}/people/guess-emails",
    response_model=list[PersonEmailGuessResult],
)
async def guess_company_emails(
    company_id: int,
    service: EmailPatternServiceDep,
    overwrite: bool = Query(False, description="Replace existing guess emails"),
) -> list[PersonEmailGuessResult]:
    """Fill pattern emails for every eligible person at a company."""
    return await service.guess_for_company(company_id, overwrite=overwrite)
