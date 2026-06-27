"""LLM-backed cover-letter generator (interface placeholder for Module 9).

Defines the seam where an OpenAI/configurable-LLM generator will live. It is not
wired to a real provider yet; constructing it without an API key raises so the
registry (``get_generator``) transparently falls back to the template generator.
When the LLM client lands (alongside Module 12's personalization engine),
implement ``generate`` to prompt the model for a tailored letter and validate it
into a :class:`CoverLetterDraft`.
"""

from __future__ import annotations

from careerpilot.backend.config.settings import get_settings
from careerpilot.backend.schemas.cover_letter import CoverLetterDraft
from careerpilot.backend.services.cover_letter.base import (
    CoverLetterContext,
    CoverLetterGenerator,
)


class LLMCoverLetterGenerator(CoverLetterGenerator):
    """Generates letters via an LLM. Placeholder until the LLM client is built."""

    name = "llm"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            # Signals the registry to fall back to the template generator.
            raise RuntimeError(
                "LLM cover-letter generator requires CAREERPILOT_OPENAI_API_KEY"
            )
        self._settings = settings

    def generate(
        self, ctx: CoverLetterContext
    ) -> CoverLetterDraft:  # pragma: no cover - not yet implemented
        raise NotImplementedError(
            "LLM cover-letter generation is not implemented yet; the template "
            "generator is the default."
        )
