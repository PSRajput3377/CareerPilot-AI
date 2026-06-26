"""Schemas for the Email Pattern Generator (Module 6)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EmailCandidate(BaseModel):
    """A single guessed email address with its provenance."""

    email: str
    #: The template that produced it, e.g. ``"{first}.{last}"``.
    pattern: str
    #: Rank-based heuristic score in (0, 1]; higher = more common pattern.
    confidence: float = Field(ge=0.0, le=1.0)


class EmailPatternResult(BaseModel):
    """Ranked candidate emails for a person at a domain."""

    full_name: str
    domain: str
    candidates: list[EmailCandidate] = Field(default_factory=list)

    @property
    def best(self) -> EmailCandidate | None:
        """The top-ranked candidate, or ``None`` if no email could be built."""
        return self.candidates[0] if self.candidates else None


class PersonEmailGuessResult(BaseModel):
    """Outcome of guessing+filling an email for a stored person (Module 6)."""

    person_id: int
    #: True when this run wrote a pattern email onto the person.
    filled: bool = False
    #: The email now on the person (existing public email or the new guess).
    email: str | None = None
    candidates: list[EmailCandidate] = Field(default_factory=list)
