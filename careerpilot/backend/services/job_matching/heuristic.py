"""Offline heuristic job matcher (Module 8).

Deterministic fit scoring that needs no network, so matching is fully testable:

* **skill** — overlap between the profile's skills and skills detected in the
  job title + description (from a known tech vocabulary plus the profile's own
  skills). This is the dominant component.
* **title** — token overlap between the profile's preferred role and the job
  title.
* **location** — remote jobs always fit; otherwise a substring match between the
  preferred location and the job location.

The overall score is a weighted blend. A nuanced LLM matcher can register via the
base registry without changing this; the weights live here so they are explicit
and tunable.
"""

from __future__ import annotations

import re

from careerpilot.backend.schemas.job_match import MatchScore
from careerpilot.backend.services.job_matching.base import (
    JobLike,
    JobMatcher,
    ProfileLike,
)

# Component weights for the overall score (sum to 1.0).
_W_SKILL = 0.6
_W_TITLE = 0.25
_W_LOCATION = 0.15

# Common tech keywords used to detect required skills in free-text job posts.
# Profile skills are also matched verbatim, so this only needs broad coverage.
_TECH_VOCAB = frozenset(
    {
        "python", "java", "javascript", "typescript", "go", "golang", "rust",
        "ruby", "scala", "kotlin", "swift", "c", "c++", "c#", "php", "elixir",
        "react", "vue", "angular", "svelte", "next.js", "node.js", "node",
        "django", "flask", "fastapi", "rails", "spring", "express", "graphql",
        "postgresql", "postgres", "mysql", "mongodb", "redis", "kafka",
        "elasticsearch", "snowflake", "dynamodb", "sqlite",
        "aws", "gcp", "azure", "kubernetes", "docker", "terraform", "ansible",
        "ci/cd", "linux", "git", "grpc", "rest", "microservices",
        "pytorch", "tensorflow", "pandas", "numpy", "spark", "airflow",
        "machine learning", "ml", "nlp", "llm", "data engineering",
    }
)

_TOKEN = re.compile(r"[a-z0-9.+#/]+")
# Generic title words that shouldn't drive a title match on their own.
_TITLE_STOPWORDS = frozenset(
    {"senior", "junior", "staff", "principal", "lead", "i", "ii", "iii",
     "engineer", "developer", "the", "of", "and", "a", "an"}
)


def _norm(s: str) -> str:
    return s.strip().lower()


class HeuristicJobMatcher(JobMatcher):
    """Deterministic skill/title/location fit scoring."""

    name = "heuristic"

    def match(self, profile: ProfileLike, job: JobLike) -> MatchScore:
        profile_skills = {_norm(s) for s in profile.skills if s and s.strip()}
        required = self._required_skills(job, profile_skills)

        skill_score, matched, missing = self._skill_fit(profile_skills, required)
        title_score = self._title_fit(profile.preferred_role, job.title)
        location_score = self._location_fit(profile.preferred_location, job)

        overall = round(
            _W_SKILL * skill_score
            + _W_TITLE * title_score
            + _W_LOCATION * location_score,
            3,
        )
        return MatchScore(
            score=overall,
            skill_score=round(skill_score, 3),
            title_score=round(title_score, 3),
            location_score=round(location_score, 3),
            matched_skills=sorted(matched),
            missing_skills=sorted(missing),
            rationale=self._rationale(overall, matched, missing, title_score),
            matcher=self.name,
        )

    # -- components -------------------------------------------------------- #

    def _required_skills(
        self, job: JobLike, profile_skills: set[str]
    ) -> set[str]:
        """Detect skills the job calls for, from its title + description.

        Matches both the known tech vocabulary and the profile's own skills (so
        a niche skill the candidate lists is still credited if the post names
        it). Multi-word skills are matched as substrings; single tokens exactly.
        """
        text = " ".join(filter(None, [job.title, job.description])).lower()
        if not text:
            return set()
        # Strip punctuation that clings to word edges (e.g. "python." from
        # "in Python.") while preserving intra-token chars like node.js / c++.
        tokens = {t.strip("./") for t in _TOKEN.findall(text)}
        tokens.discard("")
        vocab = _TECH_VOCAB | profile_skills
        found: set[str] = set()
        for skill in vocab:
            if " " in skill or "." in skill or "/" in skill or "+" in skill:
                if skill in text:
                    found.add(skill)
            elif skill in tokens:
                found.add(skill)
        return found

    def _skill_fit(
        self, profile_skills: set[str], required: set[str]
    ) -> tuple[float, set[str], set[str]]:
        if not required:
            # No detectable requirements → neutral, not penalizing.
            return 0.5, set(), set()
        matched = profile_skills & required
        missing = required - profile_skills
        score = len(matched) / len(required)
        return score, matched, missing

    def _title_fit(self, preferred_role: str | None, title: str) -> float:
        if not preferred_role or not title:
            return 0.0
        role_tokens = self._title_tokens(preferred_role)
        job_tokens = self._title_tokens(title)
        if not role_tokens or not job_tokens:
            return 0.0
        overlap = role_tokens & job_tokens
        return len(overlap) / len(role_tokens)

    def _title_tokens(self, text: str) -> set[str]:
        return {
            t for t in _TOKEN.findall(text.lower()) if t not in _TITLE_STOPWORDS
        }

    def _location_fit(self, preferred_location: str | None, job: JobLike) -> float:
        if job.remote:
            return 1.0
        if not preferred_location or not job.location:
            return 0.5  # unknown → neutral
        pref = _norm(preferred_location)
        loc = _norm(job.location)
        if "remote" in loc:
            return 1.0
        if pref in loc or loc in pref:
            return 1.0
        # City/region token overlap as a softer signal.
        if self._title_tokens(pref) & self._title_tokens(loc):
            return 0.7
        return 0.0

    def _rationale(
        self,
        overall: float,
        matched: set[str],
        missing: set[str],
        title_score: float,
    ) -> str:
        parts = [f"Overall fit {overall:.0%}."]
        if matched:
            parts.append(f"Matches {len(matched)} skill(s): {', '.join(sorted(matched))}.")
        if missing:
            parts.append(f"Missing: {', '.join(sorted(missing))}.")
        if title_score >= 0.5:
            parts.append("Title aligns with preferred role.")
        return " ".join(parts)
