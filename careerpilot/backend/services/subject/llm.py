"""LLM-backed subject generator (interface placeholder for Module 11).

Defines the seam where an OpenAI/configurable-LLM generator will live. It is not
wired to a real provider yet; constructing it without an API key raises so the
registry (``get_generator``) transparently falls back to the template generator.
When the LLM client lands (alongside Module 12's personalization engine),
implement ``generate`` to prompt the model for subject ideas and validate them
into a :class:`SubjectResult`.
"""

from __future__ import annotations

from careerpilot.backend.config.settings import get_settings
from careerpilot.backend.schemas.subject import SubjectResult
from careerpilot.backend.services.subject.base import (
    SubjectContext,
    SubjectGenerator,
)


class LLMSubjectGenerator(SubjectGenerator):
    """Generates subjects via an LLM. Placeholder until the LLM client is built."""

    name = "llm"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            # Signals the registry to fall back to the template generator.
            raise RuntimeError(
                "LLM subject generator requires CAREERPILOT_OPENAI_API_KEY"
            )
        self._settings = settings

    def generate(
        self, ctx: SubjectContext
    ) -> SubjectResult:  # pragma: no cover - not yet implemented
        raise NotImplementedError(
            "LLM subject generation is not implemented yet; the template generator "
            "is the default."
        )
