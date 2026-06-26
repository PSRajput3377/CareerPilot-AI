"""Schemas for the Resume Parser module (Module 2).

``ParsedResume`` is the provider-agnostic output contract: every parser
implementation (heuristic, LLM-backed, third-party) returns this shape, so the
service layer and persistence are decoupled from how parsing is done.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from careerpilot.backend.schemas.user_profile import (
    EducationCreate,
    ExperienceCreate,
    SkillCreate,
)


class ParsedProject(BaseModel):
    name: str
    description: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    url: str | None = None


class ParsedResume(BaseModel):
    """Structured data extracted from a resume."""

    model_config = ConfigDict(extra="ignore")

    # Contact / identity (best-effort).
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None

    # Structured sections.
    skills: list[SkillCreate] = Field(default_factory=list)
    experiences: list[ExperienceCreate] = Field(default_factory=list)
    educations: list[EducationCreate] = Field(default_factory=list)
    projects: list[ParsedProject] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)

    # Provenance: which parser produced this (e.g. "heuristic", "openai").
    parser: str = "unknown"


class ResumeParseResult(BaseModel):
    """API response: what was parsed and (optionally) what was persisted."""

    parsed: ParsedResume
    profile_id: int | None = None
    applied: bool = False
