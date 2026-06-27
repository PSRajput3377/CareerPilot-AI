"""Unit tests for the template cover-letter generator (Module 9)."""

from __future__ import annotations

from careerpilot.backend.models.cover_letter import CoverLetterTone
from careerpilot.backend.services.cover_letter.base import (
    CoverLetterContext,
    get_generator,
)
from careerpilot.backend.services.cover_letter.template import (
    TemplateCoverLetterGenerator,
)


def _ctx(**kw) -> CoverLetterContext:
    base = dict(
        candidate_name="Jane Engineer",
        company_name="Acme",
        role_title="Backend Engineer",
        candidate_skills=["Python", "FastAPI", "AWS"],
        company_industry="Fintech",
    )
    base.update(kw)
    return CoverLetterContext(**base)


def test_generates_letter_with_key_details():
    draft = TemplateCoverLetterGenerator().generate(_ctx())
    assert "Acme" in draft.body
    assert "Backend Engineer" in draft.body
    assert "Jane Engineer" in draft.body
    assert draft.word_count > 0
    assert draft.word_count == len(draft.body.split())
    assert draft.generator == "template"


def test_subject_includes_role_and_name():
    draft = TemplateCoverLetterGenerator().generate(_ctx())
    assert "Backend Engineer" in draft.subject
    assert "Jane Engineer" in draft.subject


def test_matched_skills_take_priority():
    draft = TemplateCoverLetterGenerator().generate(
        _ctx(matched_skills=["Kubernetes", "Go"], candidate_skills=["Python"])
    )
    assert "Kubernetes" in draft.body
    assert "Go" in draft.body


def test_tone_changes_opening():
    pro = TemplateCoverLetterGenerator().generate(_ctx(tone=CoverLetterTone.PROFESSIONAL))
    eager = TemplateCoverLetterGenerator().generate(
        _ctx(tone=CoverLetterTone.ENTHUSIASTIC)
    )
    assert pro.body != eager.body
    assert pro.tone == CoverLetterTone.PROFESSIONAL
    assert eager.tone == CoverLetterTone.ENTHUSIASTIC


def test_falls_back_to_preferred_role_without_listing():
    draft = TemplateCoverLetterGenerator().generate(
        _ctx(role_title=None, preferred_role="Platform Engineer")
    )
    assert "Platform Engineer" in draft.body


def test_handles_no_role_or_skills():
    ctx = CoverLetterContext(candidate_name="Sam", company_name="Globex")
    draft = TemplateCoverLetterGenerator().generate(ctx)
    assert "Globex" in draft.body
    assert "Sam" in draft.body
    assert draft.word_count > 0


def test_includes_recent_experience_when_present():
    draft = TemplateCoverLetterGenerator().generate(
        _ctx(recent_experience="Senior Engineer at Globex")
    )
    assert "Senior Engineer at Globex" in draft.body


def test_get_generator_defaults_to_template():
    assert get_generator().name == "template"
    assert get_generator("unknown").name == "template"
    # LLM requested but no API key → graceful fallback.
    assert get_generator("llm").name == "template"
