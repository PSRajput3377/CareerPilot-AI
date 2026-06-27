"""Built-in email templates seeded on first use (Module 10).

These ship read-only so every install has working outreach/referral/follow-up
templates out of the box. Users can add their own; built-ins cannot be edited or
deleted. Placeholders are resolved by the template service from the candidate,
company, person, and job context.

Available placeholders: ``{first_name} {last_name} {full_name}`` (recipient),
``{candidate_name} {candidate_role}`` (you), ``{company} {role} {industry}``.
"""

from __future__ import annotations

from careerpilot.backend.models.email_template import TemplateCategory
from careerpilot.backend.schemas.email_template import EmailTemplateCreate

BUILTIN_TEMPLATES: list[EmailTemplateCreate] = [
    EmailTemplateCreate(
        name="cold-outreach",
        category=TemplateCategory.OUTREACH,
        description="Introduce yourself to a recruiter or hiring manager.",
        subject_template="{candidate_name} — interested in the {role} role at {company}",
        body_template=(
            "Hi {first_name},\n\n"
            "I'm {candidate_name}, a {candidate_role}, and I'm reaching out about "
            "the {role} role at {company}. My background lines up closely with what "
            "the team is looking for, and I'd love to learn more.\n\n"
            "Would you be open to a short conversation?\n\n"
            "Best,\n{candidate_name}"
        ),
    ),
    EmailTemplateCreate(
        name="referral-request",
        category=TemplateCategory.REFERRAL,
        description="Ask an employee for a referral.",
        subject_template="Quick question about {company}",
        body_template=(
            "Hi {first_name},\n\n"
            "I came across the {role} opening at {company} and was hoping to learn "
            "about your experience there. If it feels like a fit, would you be "
            "comfortable referring me? I'm happy to share my resume and a short "
            "summary to make it easy.\n\n"
            "Thanks so much,\n{candidate_name}"
        ),
    ),
    EmailTemplateCreate(
        name="follow-up",
        category=TemplateCategory.FOLLOW_UP,
        description="Gentle nudge after no reply.",
        subject_template="Following up — {role} at {company}",
        body_template=(
            "Hi {first_name},\n\n"
            "Just following up on my note about the {role} role at {company}. I "
            "remain very interested and would welcome the chance to connect when "
            "the timing works.\n\n"
            "Thanks for your time,\n{candidate_name}"
        ),
    ),
    EmailTemplateCreate(
        name="thank-you",
        category=TemplateCategory.THANK_YOU,
        description="Thank a contact after a conversation.",
        subject_template="Thank you, {first_name}",
        body_template=(
            "Hi {first_name},\n\n"
            "Thank you for taking the time to speak with me about {company}. Our "
            "conversation reinforced my interest in the {role} role, and I "
            "appreciate your insights.\n\n"
            "Warm regards,\n{candidate_name}"
        ),
    ),
]
