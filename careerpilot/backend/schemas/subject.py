"""Schemas for the Subject Generator (Module 11)."""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class SubjectStyle(enum.StrEnum):
    """The angle a subject line takes."""

    DIRECT = "direct"
    PERSONAL = "personal"
    REFERRAL = "referral"
    CURIOSITY = "curiosity"
    VALUE = "value"


class SubjectRequest(BaseModel):
    """Identifiers used to build the context for subject generation."""

    profile_id: int
    company_id: int | None = None
    person_id: int | None = None
    job_listing_id: int | None = None
    #: Cap on how many subjects to return (ranked).
    limit: int = Field(default=5, ge=1, le=20)


class SubjectCandidate(BaseModel):
    """A single generated subject line."""

    text: str
    style: SubjectStyle
    #: Rank-based heuristic score in (0, 1]; higher = stronger/more general.
    confidence: float = Field(ge=0.0, le=1.0)
    #: True when the line stayed within the recommended length budget.
    within_length: bool = True


class SubjectResult(BaseModel):
    """Ranked candidate subject lines for a context."""

    candidates: list[SubjectCandidate] = Field(default_factory=list)
    generator: str = "unknown"

    @property
    def best(self) -> SubjectCandidate | None:
        return self.candidates[0] if self.candidates else None
