"""Unit tests for the template subject generator (Module 11)."""

from __future__ import annotations

from careerpilot.backend.services.subject.base import SubjectContext, get_generator
from careerpilot.backend.services.subject.template import TemplateSubjectGenerator


def _ctx(**kw) -> SubjectContext:
    base = dict(
        candidate_name="Jane Engineer",
        candidate_first_name="Jane",
        company_name="Stripe",
        role="Backend Engineer",
        recipient_first_name="Maya",
    )
    base.update(kw)
    return SubjectContext(**base)


def test_generates_ranked_candidates():
    result = TemplateSubjectGenerator().generate(_ctx())
    assert result.best is not None
    assert result.candidates
    assert result.generator == "template"
    # Confidence values are in range.
    assert all(0.0 < c.confidence <= 1.0 for c in result.candidates)


def test_respects_limit():
    result = TemplateSubjectGenerator().generate(_ctx(limit=2))
    assert len(result.candidates) == 2


def test_includes_context_details():
    result = TemplateSubjectGenerator().generate(_ctx())
    joined = " ".join(c.text for c in result.candidates)
    assert "Stripe" in joined
    assert "Backend Engineer" in joined


def test_referral_style_requires_recipient():
    with_recipient = TemplateSubjectGenerator().generate(_ctx())
    assert any(c.style.value == "referral" for c in with_recipient.candidates)

    without = TemplateSubjectGenerator().generate(_ctx(recipient_first_name=None, limit=20))
    assert not any(c.style.value == "referral" for c in without.candidates)


def test_styles_are_varied():
    result = TemplateSubjectGenerator().generate(_ctx(limit=20))
    styles = {c.style for c in result.candidates}
    assert len(styles) >= 3  # spread across multiple angles


def test_minimal_context_still_produces_subjects():
    ctx = SubjectContext(candidate_name="Sam Lee", candidate_first_name="Sam")
    result = TemplateSubjectGenerator().generate(ctx)
    assert result.candidates  # at least the curiosity fallback
    # No dangling placeholders / empty strings.
    assert all(c.text.strip() for c in result.candidates)


def test_no_duplicate_subjects():
    result = TemplateSubjectGenerator().generate(_ctx(limit=20))
    texts = [c.text for c in result.candidates]
    assert len(texts) == len(set(texts))


def test_within_length_flag():
    result = TemplateSubjectGenerator().generate(
        _ctx(company_name="A Very Long Company Name Incorporated Worldwide Ltd")
    )
    # The flag reflects the actual length budget.
    for c in result.candidates:
        assert c.within_length == (len(c.text) <= 60)


def test_get_generator_defaults_to_template():
    assert get_generator().name == "template"
    assert get_generator("unknown").name == "template"
    assert get_generator("llm").name == "template"  # graceful fallback
