"""Company ORM model (Module 3).

Stores companies discovered via search providers. Downstream modules attach to
this aggregate: Career Page Detection (Module 4) sets the ATS fields, People
Discovery (Module 5) links people, and outreach references the company.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from careerpilot.backend.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from careerpilot.backend.models.job_listing import JobListing


class HiringStatus(enum.StrEnum):
    """Whether the company is known to be hiring."""

    HIRING = "hiring"
    NOT_HIRING = "not_hiring"
    UNKNOWN = "unknown"


class FundingStage(enum.StrEnum):
    """Coarse funding stage for filtering."""

    BOOTSTRAPPED = "bootstrapped"
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    LATE_STAGE = "late_stage"
    PUBLIC = "public"
    UNKNOWN = "unknown"


class Company(Base, TimestampMixin):
    """A company record."""

    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("name", "website", name="uq_company_name_website"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    website: Mapped[str | None] = mapped_column(String(512))
    domain: Mapped[str | None] = mapped_column(String(255), index=True)
    career_page: Mapped[str | None] = mapped_column(String(512))
    linkedin_url: Mapped[str | None] = mapped_column(String(512))

    industry: Mapped[str | None] = mapped_column(String(255), index=True)
    location: Mapped[str | None] = mapped_column(String(255))
    remote_friendly: Mapped[bool | None] = mapped_column()
    employee_count: Mapped[int | None] = mapped_column(Integer)

    # Comma-separated; normalized via the schema layer.
    tech_stack: Mapped[str | None] = mapped_column(Text)

    # Hiring platform / ATS (refined by Module 4).
    hiring_platform: Mapped[str | None] = mapped_column(String(64))

    funding_stage: Mapped[FundingStage] = mapped_column(
        Enum(FundingStage, native_enum=False, length=16),
        default=FundingStage.UNKNOWN,
        nullable=False,
    )
    hiring_status: Mapped[HiringStatus] = mapped_column(
        Enum(HiringStatus, native_enum=False, length=16),
        default=HiringStatus.UNKNOWN,
        nullable=False,
    )

    # Provenance: which discovery provider produced/last-updated this record.
    source: Mapped[str | None] = mapped_column(String(64))

    # Detected ATS platform (Module 4). `hiring_platform` retains the raw slug;
    # this stores the normalized enum once career-page detection has run.
    ats_platform: Mapped[str | None] = mapped_column(String(32))

    job_listings: Mapped[list[JobListing]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
