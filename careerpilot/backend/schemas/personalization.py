"""Schemas for the AI Personalization Engine (Module 12)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from careerpilot.backend.models.cover_letter import CoverLetterTone


class PersonalizationRequest(BaseModel):
    """Inputs to compose a personalized outreach draft.

    The engine ties together the candidate profile, the recipient, the target
    company/role, and (optionally) a base template into one tailored email.
    """

    profile_id: int
    person_id: int
    company_id: int | None = None
    job_listing_id: int | None = None
    #: Start from a stored template's body; the engine enriches it. When omitted,
    #: the engine composes the body from scratch.
    template_id: int | None = None
    tone: CoverLetterTone = CoverLetterTone.PROFESSIONAL


class PersonalizedEmail(BaseModel):
    """A composed, personalized outreach draft (not persisted, not sent)."""

    subject: str
    body: str
    tone: CoverLetterTone = CoverLetterTone.PROFESSIONAL
    #: Skills the candidate shares with the role (woven into the body).
    matched_skills: list[str] = Field(default_factory=list)
    #: Which signals made it in (recipient name, role, skills, industry, …).
    personalization_signals: list[str] = Field(default_factory=list)
    #: 0..1 — how many personalization signals were available and used.
    personalization_score: float = Field(default=0.0, ge=0.0, le=1.0)
    #: Template placeholders that could not be resolved (left intact).
    missing_placeholders: list[str] = Field(default_factory=list)
    word_count: int = 0
    engine: str = "unknown"
