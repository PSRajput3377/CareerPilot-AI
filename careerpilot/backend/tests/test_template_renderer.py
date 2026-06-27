"""Unit tests for the template renderer (Module 10)."""

from __future__ import annotations

import pytest

from careerpilot.backend.services.templating.renderer import (
    TemplateRenderError,
    extract_placeholders,
    render_template,
)


def test_extract_placeholders_distinct_in_order():
    tpl = "Hi {first_name}, {first_name} at {company} for {role}."
    assert extract_placeholders(tpl) == ["first_name", "company", "role"]


def test_render_substitutes_known_values():
    body, missing = render_template(
        "Hi {first_name} at {company}", {"first_name": "Maya", "company": "Stripe"}
    )
    assert body == "Hi Maya at Stripe"
    assert missing == []


def test_render_leaves_unknown_placeholders_intact():
    body, missing = render_template("Hi {first_name}, re: {role}", {"first_name": "Sam"})
    assert body == "Hi Sam, re: {role}"
    assert missing == ["role"]


def test_empty_value_counts_as_missing():
    body, missing = render_template("Role: {role}", {"role": ""})
    assert "{role}" in body
    assert missing == ["role"]


def test_escaped_braces_become_literals():
    body, missing = render_template("Use {{curly}} and {name}", {"name": "X"})
    assert body == "Use {curly} and X"
    assert missing == []


def test_unbalanced_braces_raise():
    with pytest.raises(TemplateRenderError):
        render_template("Hello {name", {"name": "X"})


def test_no_placeholders_passthrough():
    body, missing = render_template("Just text.", {})
    assert body == "Just text."
    assert missing == []
