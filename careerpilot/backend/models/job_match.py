"""Job match ORM model (Module 8 — Job Matching AI).

Records how well a :class:`UserProfile` (Module 1) fits a :class:`JobListing`
(Module 4) extracted from a company's career page. Matching prioritizes which
roles to pursue and feeds personalization downstream (the draft can reference the
specific role and the overlapping skills).

One row per (profile, job_listing): re-matching updates the existing score
(idempotent) instead of duplicating.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from careerpilot.backend.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from careerpilot.backend.models.job_listing import JobListing
    from careerpilot.backend.models.user_profile import UserProfile


class JobMatch(Base, TimestampMixin):
    """A computed fit score between a profile and a job listing."""

    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "job_listing_id", name="uq_match_profile_listing"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    job_listing_id: Mapped[int] = mapped_column(
        ForeignKey("job_listings.id", ondelete="CASCADE"), index=True
    )

    #: Overall fit, 0..1.
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    #: Component sub-scores (0..1), for transparency.
    skill_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    title_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    location_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Comma-separated; normalized via the schema layer.
    matched_skills: Mapped[str | None] = mapped_column(Text)
    missing_skills: Mapped[str | None] = mapped_column(Text)
    #: Human-readable rationale for the score.
    rationale: Mapped[str | None] = mapped_column(Text)
    #: Which matcher produced this result.
    matcher: Mapped[str | None] = mapped_column(String(64))

    profile: Mapped[UserProfile] = relationship()
    job_listing: Mapped[JobListing] = relationship(back_populates="matches")
