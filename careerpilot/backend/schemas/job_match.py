"""Schemas for Job Matching (Module 8)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _split_csv(value: object) -> list[str]:
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


class MatchScore(BaseModel):
    """A matcher's verdict for one (profile, job) pair (provider-agnostic, no DB)."""

    score: float = Field(default=0.0, ge=0.0, le=1.0)
    skill_score: float = Field(default=0.0, ge=0.0, le=1.0)
    title_score: float = Field(default=0.0, ge=0.0, le=1.0)
    location_score: float = Field(default=0.0, ge=0.0, le=1.0)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    rationale: str | None = None
    matcher: str = "unknown"


class JobMatchRead(BaseModel):
    """A persisted job-match record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: int
    job_listing_id: int
    score: float
    skill_score: float
    title_score: float
    location_score: float
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    rationale: str | None = None
    matcher: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _coerce_skill_lists(cls, data: object) -> object:
        """Turn stored comma-separated skill strings into lists on read."""
        matched = getattr(data, "matched_skills", None)
        missing = getattr(data, "missing_skills", None)
        if isinstance(matched, str) or isinstance(missing, str):
            return _MatchView(
                data,
                {
                    "matched_skills": _split_csv(matched),
                    "missing_skills": _split_csv(missing),
                },
            )
        return data


class JobMatchResult(BaseModel):
    """A job match enriched with the listing it refers to (for ranked output)."""

    job_listing_id: int
    title: str
    company_id: int
    match: JobMatchRead


class _MatchView:
    """Attribute proxy overriding selected fields of an ORM JobMatch on read."""

    def __init__(self, wrapped: object, overrides: dict[str, object]) -> None:
        self._wrapped = wrapped
        self._overrides = overrides

    def __getattr__(self, item: str) -> object:
        if item in self._overrides:
            return self._overrides[item]
        return getattr(self._wrapped, item)
