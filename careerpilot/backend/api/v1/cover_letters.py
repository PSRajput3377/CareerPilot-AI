"""Cover Letter Generator API routes (Module 9).

Generate a draft for a profile targeting a company (and optional role), list a
profile's drafts, and read/delete individual letters. Generated letters are
drafts for review — they are never sent from here.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from careerpilot.backend.api.dependencies import CoverLetterServiceDep
from careerpilot.backend.schemas.cover_letter import (
    CoverLetterDraft,
    CoverLetterRead,
    CoverLetterRequest,
)

router = APIRouter(tags=["cover-letters"])


@router.post(
    "/profiles/{profile_id}/cover-letters",
    response_model=CoverLetterRead | CoverLetterDraft,
)
async def generate_cover_letter(
    profile_id: int, request: CoverLetterRequest, service: CoverLetterServiceDep
) -> CoverLetterRead | CoverLetterDraft:
    """Generate a cover letter draft (persisted unless ``save`` is false)."""
    draft, saved = await service.generate(profile_id, request)
    if saved is not None:
        return CoverLetterRead.model_validate(saved)
    return draft


@router.get("/profiles/{profile_id}/cover-letters", response_model=list[CoverLetterRead])
async def list_cover_letters(
    profile_id: int,
    service: CoverLetterServiceDep,
    limit: int = Query(50, ge=1, le=200),
) -> list[CoverLetterRead]:
    """List a profile's generated cover letter drafts (newest first)."""
    letters = await service.list_for_profile(profile_id, limit=limit)
    return [CoverLetterRead.model_validate(letter) for letter in letters]


@router.get("/cover-letters/{letter_id}", response_model=CoverLetterRead)
async def get_cover_letter(
    letter_id: int, service: CoverLetterServiceDep
) -> CoverLetterRead:
    letter = await service.get(letter_id)
    return CoverLetterRead.model_validate(letter)


@router.delete("/cover-letters/{letter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cover_letter(
    letter_id: int, service: CoverLetterServiceDep
) -> None:
    await service.delete(letter_id)
