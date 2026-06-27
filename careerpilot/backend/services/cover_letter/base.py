"""Cover letter generator interface and registry (Module 9).

A generator turns a candidate + target context into a cover letter draft. Two
flavors are anticipated:

* **template** (ships now): offline, deterministic. Fills a structured,
  human-sounding template from the profile, company, and (optional) role. No
  network — fast, free, fully testable.
* **llm** (future): prompts a configurable LLM for a tailored letter. Registers
  here without changing callers; falls back to the template generator when no
  API key is configured (mirrors the resume-parser registry).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from careerpilot.backend.config.settings import get_settings
from careerpilot.backend.models.cover_letter import CoverLetterTone
from careerpilot.backend.schemas.cover_letter import CoverLetterDraft


@dataclass
class CoverLetterContext:
    """Everything a generator needs, decoupled from the ORM."""

    candidate_name: str
    company_name: str
    role_title: str | None = None
    preferred_role: str | None = None
    candidate_skills: list[str] = field(default_factory=list)
    # Skills the candidate has that the role/company calls for (from Module 8).
    matched_skills: list[str] = field(default_factory=list)
    company_industry: str | None = None
    recent_experience: str | None = None  # e.g. "Senior Engineer at Globex"
    tone: CoverLetterTone = CoverLetterTone.PROFESSIONAL


class CoverLetterGenerator(ABC):
    """Abstract base for cover letter generators."""

    name: str = "abstract"

    @abstractmethod
    def generate(self, ctx: CoverLetterContext) -> CoverLetterDraft:
        """Produce a cover letter draft from the context."""
        raise NotImplementedError


def get_generator(name: str | None = None) -> CoverLetterGenerator:
    """Return a generator by name, defaulting to config / template.

    Unknown or unavailable providers fall back to the template generator so the
    feature always works offline and in tests.
    """
    from careerpilot.backend.services.cover_letter.template import (
        TemplateCoverLetterGenerator,
    )

    requested = (name or _configured_generator()).lower()

    if requested in {"template", "default", "rules"}:
        return TemplateCoverLetterGenerator()

    if requested in {"openai", "llm"}:
        try:
            from careerpilot.backend.services.cover_letter.llm import (
                LLMCoverLetterGenerator,
            )

            return LLMCoverLetterGenerator()
        except Exception:
            # No API key / SDK missing → degrade gracefully to template.
            return TemplateCoverLetterGenerator()

    return TemplateCoverLetterGenerator()


def _configured_generator() -> str:
    settings = get_settings()
    if settings.openai_api_key:
        return settings.llm.provider
    return "template"
