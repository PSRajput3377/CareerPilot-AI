"""ATS platforms and job-listing ORM model (Module 4).

Career Page Detection identifies which Applicant Tracking System (ATS) a company
uses and extracts publicly listed jobs. Listings attach to a :class:`Company`
(Module 3) and feed Job Matching (Module 8) and outreach targeting downstream.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from careerpilot.backend.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from careerpilot.backend.models.company import Company


class ATSPlatform(enum.StrEnum):
    """Supported Applicant Tracking Systems / career-page hosts."""

    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    WORKDAY = "workday"
    SMARTRECRUITERS = "smartrecruiters"
    BAMBOOHR = "bamboohr"
    JOBVITE = "jobvite"
    ORACLE = "oracle"
    SAP_SUCCESSFACTORS = "sap_successfactors"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class JobListing(Base, TimestampMixin):
    """A publicly listed job extracted from a company's career page."""

    __tablename__ = "job_listings"
    __table_args__ = (
        # Avoid duplicate listings for the same company + external id.
        UniqueConstraint("company_id", "external_id", name="uq_job_company_external"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )

    # Identifier assigned by the ATS (used for idempotent upserts).
    external_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(255))
    employment_type: Mapped[str | None] = mapped_column(String(64))
    url: Mapped[str | None] = mapped_column(String(1024))
    description: Mapped[str | None] = mapped_column(Text)
    remote: Mapped[bool | None] = mapped_column()

    company: Mapped[Company] = relationship(back_populates="job_listings")
