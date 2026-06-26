"""Resume parser interface and registry (Module 2).

A parser turns raw resume text into a :class:`ParsedResume`. The interface keeps
the rest of the system independent of *how* parsing happens — the heuristic
parser ships now; an LLM-backed parser can register later without touching
callers (Open/Closed Principle).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from careerpilot.backend.config.settings import get_settings
from careerpilot.backend.schemas.resume import ParsedResume


class ResumeParser(ABC):
    """Abstract base for resume parsers."""

    #: Stable identifier recorded as provenance on the parsed result.
    name: str = "abstract"

    @abstractmethod
    def parse(self, text: str) -> ParsedResume:
        """Parse raw resume text into structured data."""
        raise NotImplementedError


def get_parser(name: str | None = None) -> ResumeParser:
    """Return a parser by name, defaulting to config / heuristic.

    Unknown or unavailable providers fall back to the heuristic parser so the
    feature always works offline and in tests.
    """
    from careerpilot.backend.services.resume_parsing.heuristic import HeuristicResumeParser

    requested = (name or _configured_parser()).lower()

    if requested in {"heuristic", "default", "rules"}:
        return HeuristicResumeParser()

    if requested in {"openai", "llm"}:
        try:
            from careerpilot.backend.services.resume_parsing.llm import LLMResumeParser

            return LLMResumeParser()
        except Exception:
            # No API key / SDK missing → degrade gracefully to heuristic.
            return HeuristicResumeParser()

    return HeuristicResumeParser()


def _configured_parser() -> str:
    settings = get_settings()
    # Resume parsing follows the general LLM provider setting when available,
    # but defaults to the offline heuristic parser unless a key is present.
    if settings.openai_api_key:
        return settings.llm.provider
    return "heuristic"
