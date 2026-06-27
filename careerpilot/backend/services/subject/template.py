"""Offline template subject generator (Module 11).

Deterministic, varied subject lines across a spread of proven cold-email styles.
No network, so generation is fast and fully testable. Subjects are ranked by a
simple heuristic: a stronger/more broadly effective style scores higher, and
overlong lines are penalized (recruiters skim on mobile, where ~50 chars show).

Each style is only emitted when the context supports it (e.g. the referral style
needs a recipient name), so the output is always grounded — never a subject with
a dangling placeholder.
"""

from __future__ import annotations

from careerpilot.backend.schemas.subject import (
    SubjectCandidate,
    SubjectResult,
    SubjectStyle,
)
from careerpilot.backend.services.subject.base import (
    SubjectContext,
    SubjectGenerator,
)

# Recommended subject length (chars) — beyond this, mobile clients truncate.
_LENGTH_BUDGET = 60


class TemplateSubjectGenerator(SubjectGenerator):
    """Deterministic, multi-style subject generator."""

    name = "template"

    def generate(self, ctx: SubjectContext) -> SubjectResult:
        company = ctx.company_name

        # (style, text, base_rank) — ordered by general effectiveness.
        raw: list[tuple[SubjectStyle, str | None]] = [
            (
                SubjectStyle.DIRECT,
                f"{ctx.candidate_name} — interested in the {ctx.role} role"
                + (f" at {company}" if company else "")
                if ctx.role
                else None,
            ),
            (
                SubjectStyle.REFERRAL,
                f"Quick question, {ctx.recipient_first_name}"
                if ctx.recipient_first_name
                else None,
            ),
            (
                SubjectStyle.PERSONAL,
                f"{ctx.candidate_first_name} → {company}" if company else None,
            ),
            (
                SubjectStyle.VALUE,
                f"Bringing {ctx.role} experience to {company}"
                if company and ctx.role
                else None,
            ),
            (
                SubjectStyle.CURIOSITY,
                f"A note about {company}" if company else "A quick note",
            ),
            (
                SubjectStyle.DIRECT,
                f"Exploring opportunities at {company}" if company else None,
            ),
            (
                SubjectStyle.PERSONAL,
                f"{ctx.candidate_first_name} — {ctx.role}" if ctx.role else None,
            ),
        ]

        seen: set[str] = set()
        candidates: list[SubjectCandidate] = []
        total = len(raw)
        for rank, (style, text) in enumerate(raw):
            if not text:
                continue
            key = text.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            confidence = round((total - rank) / total, 3)
            candidates.append(
                SubjectCandidate(
                    text=text,
                    style=style,
                    confidence=confidence,
                    within_length=len(text) <= _LENGTH_BUDGET,
                )
            )

        # Prefer in-length subjects without losing the style spread: stable sort
        # keeps base ranking, then floats overlong lines down.
        candidates.sort(key=lambda c: (not c.within_length,))
        candidates = candidates[: ctx.limit]
        return SubjectResult(candidates=candidates, generator=self.name)
