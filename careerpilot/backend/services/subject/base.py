"""Subject generator interface and registry (Module 11).

A generator turns an outreach context into ranked, varied subject lines. Two
flavors are anticipated:

* **template** (ships now): offline, deterministic. Assembles subjects across a
  spread of proven styles (direct, personal, referral, curiosity, value). No
  network — fast, free, fully testable.
* **llm** (future): prompts a configurable LLM for fresh subject ideas.
  Registers here without changing callers; falls back to the template generator
  when no API key is configured (mirrors the resume-parser registry).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from careerpilot.backend.config.settings import get_settings
from careerpilot.backend.schemas.subject import SubjectResult


@dataclass
class SubjectContext:
    """Everything a subject generator needs, decoupled from the ORM."""

    candidate_name: str
    candidate_first_name: str
    company_name: str | None = None
    role: str | None = None
    recipient_first_name: str | None = None
    limit: int = 5


class SubjectGenerator(ABC):
    """Abstract base for subject-line generators."""

    name: str = "abstract"

    @abstractmethod
    def generate(self, ctx: SubjectContext) -> SubjectResult:
        """Produce ranked candidate subject lines from the context."""
        raise NotImplementedError


def get_generator(name: str | None = None) -> SubjectGenerator:
    """Return a generator by name, defaulting to config / template.

    Unknown or unavailable providers fall back to the template generator so the
    feature always works offline and in tests.
    """
    from careerpilot.backend.services.subject.template import (
        TemplateSubjectGenerator,
    )

    requested = (name or _configured_generator()).lower()

    if requested in {"template", "default", "rules"}:
        return TemplateSubjectGenerator()

    if requested in {"openai", "llm"}:
        try:
            from careerpilot.backend.services.subject.llm import LLMSubjectGenerator

            return LLMSubjectGenerator()
        except Exception:
            # No API key / SDK missing → degrade gracefully to template.
            return TemplateSubjectGenerator()

    return TemplateSubjectGenerator()


def _configured_generator() -> str:
    settings = get_settings()
    if settings.openai_api_key:
        return settings.llm.provider
    return "template"
