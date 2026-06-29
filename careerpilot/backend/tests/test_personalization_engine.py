"""Unit tests for the template personalization engine (Module 12)."""

from __future__ import annotations

from careerpilot.backend.models.cover_letter import CoverLetterTone
from careerpilot.backend.services.personalization.base import (
    PersonalizationContext,
    get_engine,
)
from careerpilot.backend.services.personalization.template import (
    TemplatePersonalizationEngine,
)


def _ctx(**kw) -> PersonalizationContext:
    base = dict(
        candidate_name="Jane Engineer",
        candidate_first_name="Jane",
        recipient_name="Maya Chen",
        recipient_first_name="Maya",
        candidate_role="Backend Engineer",
        company_name="Stripe",
        company_industry="Fintech",
        role="Senior Backend Engineer",
        matched_skills=["Python", "FastAPI"],
        candidate_skills=["Python", "FastAPI", "AWS"],
        recent_experience="a Backend Engineer at Globex",
        subject="Quick question, Maya",
    )
    base.update(kw)
    return PersonalizationContext(**base)


def test_compose_from_scratch_includes_signals():
    draft = TemplatePersonalizationEngine().compose(_ctx())
    assert "Maya" in draft.body
    assert "Stripe" in draft.body
    assert "Senior Backend Engineer" in draft.body
    assert "Python" in draft.body
    assert draft.subject == "Quick question, Maya"
    assert draft.engine == "template"
    assert draft.word_count > 0


def test_personalization_score_reflects_signals():
    full = TemplatePersonalizationEngine().compose(_ctx())
    thin = TemplatePersonalizationEngine().compose(
        PersonalizationContext(
            candidate_name="Sam Lee",
            candidate_first_name="Sam",
            recipient_name="Pat Doe",
            recipient_first_name="Pat",
        )
    )
    assert full.personalization_score > thin.personalization_score
    assert 0.0 <= thin.personalization_score <= 1.0
    assert full.personalization_score <= 1.0


def test_matched_skills_surface_in_output():
    draft = TemplatePersonalizationEngine().compose(_ctx())
    assert "matched_skills" in draft.personalization_signals
    assert draft.matched_skills == ["Python", "FastAPI"]


def test_enriches_base_body_when_skills_absent():
    base = "Hi Maya,\n\nI saw the opening at Stripe.\n\nBest,\nJane"
    draft = TemplatePersonalizationEngine().compose(_ctx(base_body=base))
    # The skills line is inserted because the base didn't mention them.
    assert "Python" in draft.body
    assert draft.body.count("Hi Maya,") == 1


def test_does_not_duplicate_skills_already_in_base():
    base = "Hi Maya,\n\nI use Python and FastAPI daily.\n\nBest,\nJane"
    draft = TemplatePersonalizationEngine().compose(_ctx(base_body=base))
    # Body already names the skills → no appended skills line.
    assert draft.body.count("Python") == 1


def test_tone_affects_greeting_and_closing():
    pro = TemplatePersonalizationEngine().compose(_ctx(tone=CoverLetterTone.PROFESSIONAL))
    eager = TemplatePersonalizationEngine().compose(
        _ctx(tone=CoverLetterTone.ENTHUSIASTIC)
    )
    assert pro.body != eager.body


def test_fallback_subject_when_none_given():
    draft = TemplatePersonalizationEngine().compose(_ctx(subject=""))
    assert draft.subject  # a fallback was generated
    assert "Stripe" in draft.subject


def test_minimal_context_still_composes():
    draft = TemplatePersonalizationEngine().compose(
        PersonalizationContext(
            candidate_name="Sam Lee",
            candidate_first_name="Sam",
            recipient_name="Pat",
            recipient_first_name="Pat",
        )
    )
    assert draft.body
    assert "Pat" in draft.body
    assert "{" not in draft.body  # no dangling placeholders


def test_get_engine_defaults_to_template():
    assert get_engine().name == "template"
    assert get_engine("unknown").name == "template"
    assert get_engine("llm").name == "template"  # graceful fallback
