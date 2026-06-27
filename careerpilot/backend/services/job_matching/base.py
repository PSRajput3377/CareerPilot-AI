"""Job matcher interface and registry (Module 8).

A matcher scores how well a candidate profile fits a job listing. Two flavors
are anticipated:

* **heuristic** (ships now): offline, deterministic. Compares profile skills to
  the job's required skills (parsed from title/description), title alignment,
  and location/remote fit. No network — fully testable.
* **llm** (future): prompts a configurable LLM for a nuanced fit assessment.
  Registers here without changing callers; falls back to heuristic when no API
  key is configured (mirrors the resume-parser registry).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from careerpilot.backend.config.settings import get_settings
from careerpilot.backend.schemas.job_match import MatchScore


class ProfileLike:
    """Minimal structural view a matcher needs from a user profile."""

    def __init__(
        self,
        skills: list[str],
        preferred_role: str | None = None,
        preferred_location: str | None = None,
    ) -> None:
        self.skills = skills
        self.preferred_role = preferred_role
        self.preferred_location = preferred_location


class JobLike:
    """Minimal structural view a matcher needs from a job listing."""

    def __init__(
        self,
        title: str,
        description: str | None = None,
        location: str | None = None,
        remote: bool | None = None,
    ) -> None:
        self.title = title
        self.description = description
        self.location = location
        self.remote = remote


class JobMatcher(ABC):
    """Abstract base for job matchers."""

    name: str = "abstract"

    @abstractmethod
    def match(self, profile: ProfileLike, job: JobLike) -> MatchScore:
        """Score how well ``profile`` fits ``job``."""
        raise NotImplementedError


def get_matcher(name: str | None = None) -> JobMatcher:
    """Return a matcher by name, defaulting to config / heuristic.

    Unknown or unavailable providers fall back to the heuristic matcher so the
    feature always works offline and in tests.
    """
    from careerpilot.backend.services.job_matching.heuristic import (
        HeuristicJobMatcher,
    )

    requested = (name or _configured_matcher()).lower()

    if requested in {"heuristic", "default", "rules"}:
        return HeuristicJobMatcher()

    if requested in {"openai", "llm"}:
        try:
            from careerpilot.backend.services.job_matching.llm import LLMJobMatcher

            return LLMJobMatcher()
        except Exception:
            # No API key / SDK missing → degrade gracefully to heuristic.
            return HeuristicJobMatcher()

    return HeuristicJobMatcher()


def _configured_matcher() -> str:
    settings = get_settings()
    # Follow the general LLM provider setting when a key is present; otherwise
    # use the offline heuristic matcher.
    if settings.openai_api_key:
        return settings.llm.provider
    return "heuristic"
