"""Personalization engine interface and registry (Module 12).

An engine turns a fully-resolved context into a personalized outreach draft.
Two flavors are anticipated:

* **template** (ships now): offline, deterministic. Weaves the recipient, role,
  company, and the candidate's overlapping skills into a human-sounding email —
  either enriching a chosen base template or composing from scratch. No network.
* **llm** (future): prompts a configurable LLM for a bespoke message. Registers
  here without changing callers; falls back to the template engine when no API
  key is configured (mirrors the resume-parser registry).

The engine never sends: it produces a reviewable draft (the human-in-the-loop
gate lives downstream in outreach/sending).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from careerpilot.backend.config.settings import get_settings
from careerpilot.backend.models.cover_letter import CoverLetterTone
from careerpilot.backend.schemas.personalization import PersonalizedEmail


@dataclass
class PersonalizationContext:
    """Everything an engine needs, decoupled from the ORM."""

    candidate_name: str
    candidate_first_name: str
    recipient_name: str
    recipient_first_name: str
    candidate_role: str | None = None
    company_name: str | None = None
    company_industry: str | None = None
    role: str | None = None
    matched_skills: list[str] = field(default_factory=list)
    candidate_skills: list[str] = field(default_factory=list)
    recent_experience: str | None = None
    subject: str = ""
    # A pre-rendered base body (from a template) to enrich; empty = compose.
    base_body: str = ""
    missing_placeholders: list[str] = field(default_factory=list)
    tone: CoverLetterTone = CoverLetterTone.PROFESSIONAL


class PersonalizationEngine(ABC):
    """Abstract base for personalization engines."""

    name: str = "abstract"

    @abstractmethod
    def compose(self, ctx: PersonalizationContext) -> PersonalizedEmail:
        """Compose a personalized outreach draft from the context."""
        raise NotImplementedError


def get_engine(name: str | None = None) -> PersonalizationEngine:
    """Return an engine by name, defaulting to config / template.

    Unknown or unavailable providers fall back to the template engine so the
    feature always works offline and in tests.
    """
    from careerpilot.backend.services.personalization.template import (
        TemplatePersonalizationEngine,
    )

    requested = (name or _configured_engine()).lower()

    if requested in {"template", "default", "rules"}:
        return TemplatePersonalizationEngine()

    if requested in {"openai", "llm"}:
        try:
            from careerpilot.backend.services.personalization.llm import (
                LLMPersonalizationEngine,
            )

            return LLMPersonalizationEngine()
        except Exception:
            # No API key / SDK missing → degrade gracefully to template.
            return TemplatePersonalizationEngine()

    return TemplatePersonalizationEngine()


def _configured_engine() -> str:
    settings = get_settings()
    if settings.openai_api_key:
        return settings.llm.provider
    return "template"
