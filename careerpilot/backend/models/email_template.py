"""Email template ORM model (Module 10 — Email Template Engine).

Reusable, named email templates with ``{placeholder}`` slots that render against
a context (the candidate, the target company, the recipient person, and an
optional role). Templates standardize the structure of outreach while the
rendered text stays individual — the personalization engine (Module 12) and
the sender (Module 15) consume rendered output, but rendering itself never
sends.

Built-in templates ship seeded and read-only; users can add their own.
"""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, Enum, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from careerpilot.backend.database.base import Base, TimestampMixin


class TemplateCategory(enum.StrEnum):
    """What stage of outreach a template is for."""

    OUTREACH = "outreach"
    REFERRAL = "referral"
    FOLLOW_UP = "follow_up"
    THANK_YOU = "thank_you"
    OTHER = "other"


class EmailTemplate(Base, TimestampMixin):
    """A reusable email template with placeholder slots."""

    __tablename__ = "email_templates"
    __table_args__ = (UniqueConstraint("name", name="uq_email_template_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    category: Mapped[TemplateCategory] = mapped_column(
        Enum(TemplateCategory, native_enum=False, length=16),
        default=TemplateCategory.OUTREACH,
        nullable=False,
    )

    # Templates carry ``{placeholder}`` tokens; rendering substitutes them.
    subject_template: Mapped[str] = mapped_column(String(512), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)

    description: Mapped[str | None] = mapped_column(String(512))
    # Seeded, read-only templates cannot be edited or deleted.
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
