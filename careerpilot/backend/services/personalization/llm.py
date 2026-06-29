"""LLM-backed personalization engine (interface placeholder for Module 12).

Defines the seam where an OpenAI/configurable-LLM engine will live. It is not
wired to a real provider yet; constructing it without an API key raises so the
registry (``get_engine``) transparently falls back to the template engine. When
the LLM client lands, implement ``compose`` to prompt the model for a tailored
message and validate it into a :class:`PersonalizedEmail`.
"""

from __future__ import annotations

from careerpilot.backend.config.settings import get_settings
from careerpilot.backend.schemas.personalization import PersonalizedEmail
from careerpilot.backend.services.personalization.base import (
    PersonalizationContext,
    PersonalizationEngine,
)


class LLMPersonalizationEngine(PersonalizationEngine):
    """Composes via an LLM. Placeholder until the LLM client is built."""

    name = "llm"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            # Signals the registry to fall back to the template engine.
            raise RuntimeError(
                "LLM personalization engine requires CAREERPILOT_OPENAI_API_KEY"
            )
        self._settings = settings

    def compose(
        self, ctx: PersonalizationContext
    ) -> PersonalizedEmail:  # pragma: no cover - not yet implemented
        raise NotImplementedError(
            "LLM personalization is not implemented yet; the template engine is "
            "the default."
        )
