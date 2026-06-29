"""Offline template personalization engine (Module 12).

Deterministic composition that needs no network, so it is fast and fully
testable. It either **enriches** a chosen base template body (appending a
grounded personalization line when the template didn't already mention the
overlapping skills) or **composes** a human-sounding message from scratch.

The personalization score reflects how many individual signals (recipient name,
role, company, industry, overlapping skills, recent experience) were available
and woven in — a transparency hook so a thin draft is easy to spot before it
goes out for review.
"""

from __future__ import annotations

from careerpilot.backend.models.cover_letter import CoverLetterTone
from careerpilot.backend.schemas.personalization import PersonalizedEmail
from careerpilot.backend.services.personalization.base import (
    PersonalizationContext,
    PersonalizationEngine,
)

# Signals tracked for the personalization score (each present = +1).
_SIGNAL_WEIGHTS = 6

_GREETING = {
    CoverLetterTone.PROFESSIONAL: "Hi {name},",
    CoverLetterTone.ENTHUSIASTIC: "Hi {name}!",
    CoverLetterTone.CONCISE: "Hi {name},",
}

_CLOSING = {
    CoverLetterTone.PROFESSIONAL: "Best regards,\n{candidate}",
    CoverLetterTone.ENTHUSIASTIC: "Looking forward to connecting,\n{candidate}",
    CoverLetterTone.CONCISE: "Thanks,\n{candidate}",
}


class TemplatePersonalizationEngine(PersonalizationEngine):
    """Deterministic personalization composer."""

    name = "template"

    def compose(self, ctx: PersonalizationContext) -> PersonalizedEmail:
        signals = self._collect_signals(ctx)
        if ctx.base_body:
            body = self._enrich(ctx)
        else:
            body = self._compose(ctx)

        score = round(len(signals) / _SIGNAL_WEIGHTS, 3)
        subject = ctx.subject or self._fallback_subject(ctx)
        return PersonalizedEmail(
            subject=subject,
            body=body,
            tone=ctx.tone,
            matched_skills=list(ctx.matched_skills),
            personalization_signals=signals,
            personalization_score=min(score, 1.0),
            missing_placeholders=list(ctx.missing_placeholders),
            word_count=len(body.split()),
            engine=self.name,
        )

    # -- signal accounting ------------------------------------------------- #

    def _collect_signals(self, ctx: PersonalizationContext) -> list[str]:
        signals: list[str] = []
        if ctx.recipient_first_name:
            signals.append("recipient_name")
        if ctx.role:
            signals.append("role")
        if ctx.company_name:
            signals.append("company")
        if ctx.company_industry:
            signals.append("industry")
        if ctx.matched_skills:
            signals.append("matched_skills")
        if ctx.recent_experience:
            signals.append("recent_experience")
        return signals

    # -- composition ------------------------------------------------------- #

    def _enrich(self, ctx: PersonalizationContext) -> str:
        """Append a grounded line to a base template body when it adds signal."""
        body = ctx.base_body.rstrip()
        addition = self._skills_line(ctx)
        if addition and ctx.matched_skills:
            # Only append if the body doesn't already name these skills.
            lowered = body.lower()
            if not any(s.lower() in lowered for s in ctx.matched_skills):
                body = self._insert_before_closing(body, addition)
        return body

    def _compose(self, ctx: PersonalizationContext) -> str:
        paragraphs: list[str] = []
        greeting = _GREETING[ctx.tone].format(name=ctx.recipient_first_name or "there")
        paragraphs.append(greeting)

        role = ctx.role or ctx.candidate_role or "an open role"
        company = ctx.company_name or "your team"
        opener = (
            f"I'm {ctx.candidate_name}, reaching out about the {role} at {company}."
        )
        paragraphs.append(opener)

        grounding: list[str] = []
        if ctx.recent_experience:
            grounding.append(
                f"I'm currently {ctx.recent_experience}, and I'm exploring my next move."
            )
        skills_line = self._skills_line(ctx)
        if skills_line:
            grounding.append(skills_line)
        if grounding:
            paragraphs.append(" ".join(grounding))

        if ctx.company_industry:
            paragraphs.append(
                f"I've been following {company}'s work in {ctx.company_industry}, "
                "and I'd love to contribute."
            )

        if ctx.tone == CoverLetterTone.CONCISE:
            paragraphs.append("Would you be open to a quick chat?")
        else:
            paragraphs.append(
                "Would you be open to a short conversation about how I could help?"
            )

        paragraphs.append(_CLOSING[ctx.tone].format(candidate=ctx.candidate_name))
        return "\n\n".join(paragraphs)

    def _skills_line(self, ctx: PersonalizationContext) -> str:
        skills = ctx.matched_skills or ctx.candidate_skills
        if not skills:
            return ""
        listed = _humanize_list(skills[:4])
        role = ctx.role or "the role"
        if ctx.matched_skills:
            return (
                f"My experience with {listed} lines up closely with what {role} calls for."
            )
        return f"My background spans {listed}."

    def _insert_before_closing(self, body: str, addition: str) -> str:
        """Insert a line above the signature block if one is detectable."""
        lines = body.split("\n\n")
        if len(lines) >= 2:
            lines.insert(len(lines) - 1, addition)
            return "\n\n".join(lines)
        return f"{body}\n\n{addition}"

    def _fallback_subject(self, ctx: PersonalizationContext) -> str:
        if ctx.company_name and ctx.role:
            return f"{ctx.candidate_name} — {ctx.role} at {ctx.company_name}"
        if ctx.company_name:
            return f"{ctx.candidate_first_name} → {ctx.company_name}"
        return f"Introduction — {ctx.candidate_name}"


def _humanize_list(items: list[str]) -> str:
    items = [i for i in items if i and i.strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"
