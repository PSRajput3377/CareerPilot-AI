"""Deterministic business-email pattern generator (Module 6).

Given a person's name and a company domain, produce a ranked list of candidate
addresses from common corporate conventions (``first.last@``, ``flast@``, …).
This is the ``no public email found → generate common patterns`` branch of the
outreach pipeline. It is offline, deterministic, and needs no network.

Generated addresses are **guesses**: they carry ``email_source = pattern`` and
must be verified (Module 7) before any send. Ranking is purely heuristic —
earlier templates in the configured list are more common, so they score higher.
"""

from __future__ import annotations

import re

from careerpilot.backend.config.settings import get_settings
from careerpilot.backend.schemas.email_pattern import (
    EmailCandidate,
    EmailPatternResult,
)

# Strip accents/punctuation to an email-safe ascii local part.
_NON_LOCAL = re.compile(r"[^a-z0-9]+")


def _normalize(token: str) -> str:
    """Lowercase and reduce a name token to email-safe characters."""
    return _NON_LOCAL.sub("", token.lower())


class EmailPatternGenerator:
    """Builds ranked candidate emails from a name + domain."""

    def __init__(
        self,
        templates: list[str] | None = None,
        max_candidates: int | None = None,
    ) -> None:
        cfg = get_settings().email_patterns
        self._templates = templates if templates is not None else list(cfg.templates)
        self._max = max_candidates if max_candidates is not None else cfg.max_candidates

    def generate(self, full_name: str, domain: str) -> EmailPatternResult:
        """Return ranked candidate emails for ``full_name`` at ``domain``.

        Templates that cannot be rendered (e.g. ``{last}`` for a single-word
        name) are skipped. Duplicate local parts are de-duplicated, keeping the
        highest-ranked occurrence. Confidence decays by rank.
        """
        domain = _normalize_domain(domain)
        first, last = self._split_name(full_name)
        result = EmailPatternResult(full_name=full_name, domain=domain)
        if not domain or not first:
            return result

        fields = {
            "first": first,
            "last": last,
            "f": first[:1],
            "l": last[:1] if last else "",
        }

        seen: set[str] = set()
        candidates: list[EmailCandidate] = []
        total = len(self._templates)
        for rank, template in enumerate(self._templates):
            local = self._render(template, fields)
            if not local or local in seen:
                continue
            seen.add(local)
            confidence = round((total - rank) / total, 3)
            candidates.append(
                EmailCandidate(
                    email=f"{local}@{domain}",
                    pattern=template,
                    confidence=confidence,
                )
            )
            if len(candidates) >= self._max:
                break

        result.candidates = candidates
        return result

    # -- internals --------------------------------------------------------- #

    def _split_name(self, full_name: str) -> tuple[str, str]:
        """Split into normalized (first, last); last is '' for single names."""
        parts = [_normalize(p) for p in full_name.split()]
        parts = [p for p in parts if p]
        if not parts:
            return "", ""
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], parts[-1]

    def _render(self, template: str, fields: dict[str, str]) -> str | None:
        """Render a template, or ``None`` if a referenced field is empty."""
        try:
            local = template.format(**fields)
        except (KeyError, IndexError):
            return None
        # A template relying on an empty field (e.g. {last} for a mononym)
        # collapses to a partial/empty local part — reject those.
        if "{last}" in template and not fields["last"]:
            return None
        if "{l}" in template and not fields["l"]:
            return None
        # Name tokens are already email-safe; only template separators (. _)
        # remain. Trim any that ended up leading/trailing.
        local = local.strip("._")
        return local or None


def _normalize_domain(domain: str) -> str:
    """Reduce a website/domain to a bare hostname (drop scheme, path, www)."""
    domain = (domain or "").strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0]
    domain = re.sub(r"^www\.", "", domain)
    return domain
