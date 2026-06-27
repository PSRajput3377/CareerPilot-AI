"""Cover letter ORM model (Module 9 — Cover Letter Generator).

Stores cover letters generated for a :class:`UserProfile` (Module 1) targeting a
:class:`Company` (Module 3) and optionally a specific :class:`JobListing`
(Module 4). A generated letter is a *draft*: it lands here to be reviewed and
edited before it is ever sent, honoring the human-in-the-loop gate of the
outreach contract.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from careerpilot.backend.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from careerpilot.backend.models.company import Company
    from careerpilot.backend.models.job_listing import JobListing
    from careerpilot.backend.models.user_profile import UserProfile


class CoverLetterTone(enum.StrEnum):
    """Voice the letter is written in."""

    PROFESSIONAL = "professional"
    ENTHUSIASTIC = "enthusiastic"
    CONCISE = "concise"


class CoverLetter(Base, TimestampMixin):
    """A generated, reviewable cover letter draft."""

    __tablename__ = "cover_letters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    # Optional: a letter may target a specific role or be company-general.
    job_listing_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_listings.id", ondelete="SET NULL"), index=True
    )

    subject: Mapped[str | None] = mapped_column(String(512))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[CoverLetterTone] = mapped_column(
        Enum(CoverLetterTone, native_enum=False, length=16),
        default=CoverLetterTone.PROFESSIONAL,
        nullable=False,
    )
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Which generator produced this draft.
    generator: Mapped[str | None] = mapped_column(String(64))

    profile: Mapped[UserProfile] = relationship()
    company: Mapped[Company] = relationship()
    job_listing: Mapped[JobListing | None] = relationship()
