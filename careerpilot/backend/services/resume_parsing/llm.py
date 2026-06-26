"""LLM-backed resume parser (interface placeholder for Module 2).

Defines the seam where an OpenAI/configurable-LLM parser will live. It is not
wired to a real provider yet; constructing it without an API key raises so the
registry (``get_parser``) transparently falls back to the heuristic parser. When
the LLM client lands (alongside Module 12's personalization engine), implement
``parse`` to prompt the model for a JSON ``ParsedResume`` and validate it.
"""

from __future__ import annotations

from careerpilot.backend.config.settings import get_settings
from careerpilot.backend.schemas.resume import ParsedResume
from careerpilot.backend.services.resume_parsing.base import ResumeParser


class LLMResumeParser(ResumeParser):
    """Parses resumes via an LLM. Placeholder until the LLM client is built."""

    name = "llm"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            # Signals the registry to fall back to the heuristic parser.
            raise RuntimeError("LLM resume parser requires CAREERPILOT_OPENAI_API_KEY")
        self._settings = settings

    def parse(self, text: str) -> ParsedResume:  # pragma: no cover - not yet implemented
        raise NotImplementedError(
            "LLM resume parsing is not implemented yet; the heuristic parser is the default."
        )
