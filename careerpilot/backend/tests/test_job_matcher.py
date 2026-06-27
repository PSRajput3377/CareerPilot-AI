"""Unit tests for the offline heuristic job matcher (Module 8)."""

from __future__ import annotations

from careerpilot.backend.services.job_matching.base import (
    JobLike,
    ProfileLike,
    get_matcher,
)
from careerpilot.backend.services.job_matching.heuristic import HeuristicJobMatcher


def _matcher() -> HeuristicJobMatcher:
    return HeuristicJobMatcher()


def test_strong_match_scores_high():
    profile = ProfileLike(
        skills=["Python", "FastAPI", "PostgreSQL", "AWS"],
        preferred_role="Backend Engineer",
        preferred_location="Remote",
    )
    job = JobLike(
        title="Senior Backend Engineer",
        description="We use Python, FastAPI and PostgreSQL on AWS.",
        location="San Francisco",
        remote=True,
    )
    result = _matcher().match(profile, job)

    assert result.score > 0.8
    assert "python" in result.matched_skills
    assert "fastapi" in result.matched_skills
    assert result.location_score == 1.0  # remote
    assert result.title_score > 0  # "backend" overlaps
    assert result.matcher == "heuristic"


def test_weak_match_scores_low():
    profile = ProfileLike(
        skills=["Photoshop", "Illustrator"],
        preferred_role="Graphic Designer",
        preferred_location="New York",
    )
    job = JobLike(
        title="Senior Backend Engineer",
        description="Python, Go, Kubernetes required.",
        location="Berlin",
        remote=False,
    )
    result = _matcher().match(profile, job)
    assert result.score < 0.3
    assert "python" in result.missing_skills


def test_remote_job_gets_full_location_score():
    profile = ProfileLike(skills=["Python"], preferred_location="Tokyo")
    job = JobLike(title="Engineer", description="Python", remote=True, location=None)
    assert _matcher().match(profile, job).location_score == 1.0


def test_location_substring_match():
    profile = ProfileLike(skills=["Python"], preferred_location="San Francisco, CA")
    job = JobLike(
        title="Engineer", description="Python", location="San Francisco", remote=False
    )
    assert _matcher().match(profile, job).location_score == 1.0


def test_no_detectable_requirements_is_neutral():
    profile = ProfileLike(skills=["Python"], preferred_role="Engineer")
    job = JobLike(title="Some Role", description="A great opportunity to grow.")
    result = _matcher().match(profile, job)
    # No skills detected → neutral skill score, not zero.
    assert result.skill_score == 0.5
    assert result.matched_skills == []


def test_skills_detected_from_profile_vocab():
    # A niche skill not in the base vocab is still credited if the post names it.
    profile = ProfileLike(skills=["Elasticsearch", "Clojure"])
    job = JobLike(title="Engineer", description="Experience with Clojure preferred.")
    result = _matcher().match(profile, job)
    assert "clojure" in result.matched_skills


def test_multiword_skill_detection():
    profile = ProfileLike(skills=["Machine Learning", "Python"])
    job = JobLike(
        title="ML Engineer", description="Strong machine learning background in Python."
    )
    result = _matcher().match(profile, job)
    assert "machine learning" in result.matched_skills
    assert "python" in result.matched_skills


def test_score_components_bounded():
    profile = ProfileLike(skills=["Python"], preferred_role="Engineer")
    job = JobLike(title="Engineer", description="Python", remote=True)
    r = _matcher().match(profile, job)
    for v in (r.score, r.skill_score, r.title_score, r.location_score):
        assert 0.0 <= v <= 1.0


def test_get_matcher_defaults_to_heuristic():
    assert get_matcher().name == "heuristic"
    assert get_matcher("unknown").name == "heuristic"
    # LLM requested but no API key → graceful fallback.
    assert get_matcher("llm").name == "heuristic"
