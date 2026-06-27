"""Offline template cover-letter generator (Module 9).

Deterministic, human-sounding letters assembled from the candidate + target
context. No network, so generation is fast and fully testable. The output is a
*draft* meant for human review and editing before sending (the outreach
contract's human-in-the-loop gate).

Tone shapes the opening and closing; the body always grounds the letter in
concrete, individual details (the specific role, the company, and the
candidate's overlapping skills) so it reads as personal rather than templated.
"""

from __future__ import annotations

from careerpilot.backend.models.cover_letter import CoverLetterTone
from careerpilot.backend.schemas.cover_letter import CoverLetterDraft
from careerpilot.backend.services.cover_letter.base import (
    CoverLetterContext,
    CoverLetterGenerator,
)

_OPENINGS = {
    CoverLetterTone.PROFESSIONAL: (
        "I am writing to express my interest in the {role} role at {company}."
    ),
    CoverLetterTone.ENTHUSIASTIC: (
        "I was genuinely excited to come across the {role} opening at {company} — "
        "it lines up closely with the work I love doing."
    ),
    CoverLetterTone.CONCISE: "I'd like to be considered for the {role} role at {company}.",
}

_CLOSINGS = {
    CoverLetterTone.PROFESSIONAL: (
        "I would welcome the opportunity to discuss how I can contribute to {company}. "
        "Thank you for your time and consideration."
    ),
    CoverLetterTone.ENTHUSIASTIC: (
        "I'd love the chance to talk about how I can help {company} keep building great "
        "things. Thanks so much for considering my application!"
    ),
    CoverLetterTone.CONCISE: (
        "I'd welcome a chance to talk further. Thank you for your consideration."
    ),
}


class TemplateCoverLetterGenerator(CoverLetterGenerator):
    """Deterministic, tone-aware template generator."""

    name = "template"

    def generate(self, ctx: CoverLetterContext) -> CoverLetterDraft:
        role = ctx.role_title or ctx.preferred_role or "the open"
        subject = self._subject(ctx, role)
        body = self._body(ctx, role)
        return CoverLetterDraft(
            subject=subject,
            body=body,
            tone=ctx.tone,
            word_count=len(body.split()),
            generator=self.name,
        )

    # -- internals --------------------------------------------------------- #

    def _subject(self, ctx: CoverLetterContext, role: str) -> str:
        role_label = role if role != "the open" else "Open Role"
        return f"Application for {role_label} — {ctx.candidate_name}"

    def _body(self, ctx: CoverLetterContext, role: str) -> str:
        paragraphs: list[str] = []

        paragraphs.append(_OPENINGS[ctx.tone].format(role=role, company=ctx.company_name))

        # Grounding paragraph: experience + skills.
        grounding: list[str] = []
        if ctx.recent_experience:
            grounding.append(
                f"Most recently I worked as {ctx.recent_experience}, where I "
                "delivered production software end to end."
            )
        highlight = ctx.matched_skills or ctx.candidate_skills
        if highlight:
            skills = _humanize_list(highlight[:5])
            grounding.append(
                f"My background spans {skills}, which maps directly to what the "
                f"{role} role calls for."
            )
        if not grounding:
            grounding.append(
                "My background has prepared me to make an immediate contribution "
                f"in the {role} role."
            )
        paragraphs.append(" ".join(grounding))

        # Company-fit paragraph.
        if ctx.company_industry:
            paragraphs.append(
                f"What draws me to {ctx.company_name} is its work in "
                f"{ctx.company_industry}; I'm eager to bring my experience to a team "
                "solving problems at that scale."
            )
        else:
            paragraphs.append(
                f"I admire what {ctx.company_name} is building and would be glad to "
                "contribute to the team's continued momentum."
            )

        paragraphs.append(_CLOSINGS[ctx.tone].format(company=ctx.company_name))
        paragraphs.append(f"Best regards,\n{ctx.candidate_name}")

        return "\n\n".join(paragraphs)


def _humanize_list(items: list[str]) -> str:
    """Join skills as 'a, b, and c'."""
    items = [i for i in items if i and i.strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"
