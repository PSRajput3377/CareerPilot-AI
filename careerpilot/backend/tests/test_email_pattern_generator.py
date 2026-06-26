"""Unit tests for the deterministic email pattern generator (Module 6)."""

from __future__ import annotations

from careerpilot.backend.services.email_pattern.generator import EmailPatternGenerator


def _gen(**kw) -> EmailPatternGenerator:
    return EmailPatternGenerator(**kw)


def test_generates_ranked_candidates_for_default_templates():
    result = _gen().generate("Jane Doe", "example.com")
    emails = [c.email for c in result.candidates]

    assert result.best is not None
    assert result.best.email == "jane.doe@example.com"
    assert "jdoe@example.com" in emails
    # Confidence is strictly decreasing by rank.
    confs = [c.confidence for c in result.candidates]
    assert confs == sorted(confs, reverse=True)


def test_respects_max_candidates():
    result = _gen(max_candidates=3).generate("Jane Doe", "example.com")
    assert len(result.candidates) == 3


def test_custom_templates_only():
    result = _gen(templates=["{first}.{last}", "{f}{last}"]).generate(
        "Ada Lovelace", "acme.io"
    )
    assert [c.email for c in result.candidates] == [
        "ada.lovelace@acme.io",
        "alovelace@acme.io",
    ]


def test_normalizes_domain_and_name():
    result = _gen().generate("  Élena  O'Brien ", "https://www.Example.com/jobs")
    assert result.domain == "example.com"
    # Accents/punctuation stripped to ascii-safe local parts.
    assert result.best is not None
    assert result.best.email == "lena.obrien@example.com"


def test_single_word_name_skips_last_templates():
    result = _gen().generate("Cher", "example.com")
    emails = [c.email for c in result.candidates]
    assert "cher@example.com" in emails
    # No template needing a last name should appear.
    assert all("{last}" not in c.pattern and "{l}" not in c.pattern for c in result.candidates)


def test_no_domain_returns_no_candidates():
    result = _gen().generate("Jane Doe", "")
    assert result.candidates == []
    assert result.best is None


def test_dedupes_identical_local_parts():
    # {first}{last} and a hypothetical duplicate should not both appear.
    result = _gen(templates=["{first}.{last}", "{first}.{last}"]).generate(
        "Jane Doe", "example.com"
    )
    assert len(result.candidates) == 1
