"""LLM-backed job matcher (interface placeholder for Module 8).

Defines the seam where an OpenAI/configurable-LLM matcher will live. It is not
wired to a real provider yet; constructing it without an API key raises so the
registry (``get_matcher``) transparently falls back to the heuristic matcher.
When the LLM client lands (alongside Module 12's personalization engine),
implement ``match`` to prompt the model for a JSON :class:`MatchScore` and
validate it.
"""

from __future__ import annotations

from careerpilot.backend.config.settings import get_settings
from careerpilot.backend.schemas.job_match import MatchScore
from careerpilot.backend.services.job_matching.base import (
    JobLike,
    JobMatcher,
    ProfileLike,
)


class LLMJobMatcher(JobMatcher):
    """Scores fit via an LLM. Placeholder until the LLM client is built."""

    name = "llm"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            # Signals the registry to fall back to the heuristic matcher.
            raise RuntimeError("LLM job matcher requires CAREERPILOT_OPENAI_API_KEY")
        self._settings = settings

    def match(
        self, profile: ProfileLike, job: JobLike
    ) -> MatchScore:  # pragma: no cover - not yet implemented
        raise NotImplementedError(
            "LLM job matching is not implemented yet; the heuristic matcher is the default."
        )
