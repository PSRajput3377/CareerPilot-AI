"""Schemas for the Cover Letter Generator (Module 9)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from careerpilot.backend.models.cover_letter import CoverLetterTone


class CoverLetterRequest(BaseModel):
    """Inputs for generating a cover letter."""

    company_id: int
    job_listing_id: int | None = Field(
        default=None, description="Target a specific role; omit for company-general"
    )
    tone: CoverLetterTone = CoverLetterTone.PROFESSIONAL
    #: When false, the draft is returned but not persisted (preview).
    save: bool = True


class CoverLetterDraft(BaseModel):
    """A generated cover letter, before persistence (generator output)."""

    subject: str
    body: str
    tone: CoverLetterTone = CoverLetterTone.PROFESSIONAL
    word_count: int = 0
    generator: str = "unknown"


class CoverLetterRead(BaseModel):
    """A persisted cover letter draft."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: int
    company_id: int
    job_listing_id: int | None = None
    subject: str | None = None
    body: str
    tone: CoverLetterTone
    word_count: int
    generator: str | None = None
    created_at: datetime
    updated_at: datetime
