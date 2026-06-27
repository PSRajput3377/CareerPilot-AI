"""Placeholder rendering for email templates (Module 10).

Templates use ``{placeholder}`` tokens. Rendering substitutes known values and
leaves unknown placeholders **intact** (rather than erroring or blanking) so a
partially-resolvable template still produces useful, reviewable text — the
caller is told which placeholders were missing.

Literal braces are written ``{{`` / ``}}`` (mirroring :meth:`str.format`).
"""

from __future__ import annotations

import re

# Matches a single {placeholder} but not the escaped {{ or }} literals.
_PLACEHOLDER = re.compile(r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})")


class TemplateRenderError(ValueError):
    """Raised when a template is malformed (e.g. unbalanced braces)."""


def extract_placeholders(template: str) -> list[str]:
    """Return the distinct placeholder names used in ``template``, in order."""
    seen: dict[str, None] = {}
    for match in _PLACEHOLDER.finditer(template):
        seen.setdefault(match.group(1), None)
    return list(seen)


def render_template(
    template: str, values: dict[str, str]
) -> tuple[str, list[str]]:
    """Render ``template`` with ``values``.

    Returns the rendered string and the list of placeholders that had no value
    (left intact in the output). Escaped ``{{``/``}}`` become literal braces.
    """
    _validate_braces(template)
    missing: list[str] = []

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in values and values[key] is not None and values[key] != "":
            return str(values[key])
        if key not in missing:
            missing.append(key)
        return match.group(0)  # leave the {placeholder} intact

    rendered = _PLACEHOLDER.sub(_sub, template)
    # Collapse escaped braces last so a literal "{{name}}" is preserved as text.
    rendered = rendered.replace("{{", "{").replace("}}", "}")
    return rendered, missing


def _validate_braces(template: str) -> None:
    """Reject obviously malformed templates (lone, unmatched braces)."""
    stripped = template.replace("{{", "").replace("}}", "")
    # After removing escaped + valid {tokens}, no stray brace should remain.
    leftover = _PLACEHOLDER.sub("", stripped)
    if "{" in leftover or "}" in leftover:
        raise TemplateRenderError(
            "Template has unbalanced or invalid braces; escape literals as {{ }}."
        )
