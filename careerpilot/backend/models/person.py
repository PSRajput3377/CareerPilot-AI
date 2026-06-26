"""Person ORM model (Module 5 — People Discovery).

Stores recruiters and employees discovered at a :class:`Company` (Module 3).
People are the outreach targets: downstream modules verify their email
(Module 7), draft a personalized message (Module 12), and — only after the human
review gate — send it (Module 15).

Email provenance matters for the orchestration contract: a ``public`` email
(found on a public page) is preferred over a ``pattern`` guess, and nothing is
auto-sent to an unverified address. The ``email_source`` and ``email_verified``
fields carry that signal forward.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from careerpilot.backend.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from careerpilot.backend.models.company import Company


class PersonRole(enum.StrEnum):
    """Coarse role classification used to prioritize outreach targets."""

    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    EXECUTIVE = "executive"
    ENGINEER = "engineer"
    EMPLOYEE = "employee"
    UNKNOWN = "unknown"


class EmailSource(enum.StrEnum):
    """Where a person's email came from (drives verified-email-first policy)."""

    #: Found published on a public page — most trustworthy.
    PUBLIC = "public"
    #: Synthesized from a company email pattern (Module 6) — a guess.
    PATTERN = "pattern"
    UNKNOWN = "unknown"


class Person(Base, TimestampMixin):
    """A recruiter or employee at a company — a potential outreach target."""

    __tablename__ = "people"
    __table_args__ = (
        # Avoid duplicate people for the same company + provider identity.
        UniqueConstraint("company_id", "external_id", name="uq_person_company_external"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )

    # Identifier assigned by the discovery provider (used for idempotent upserts).
    external_id: Mapped[str | None] = mapped_column(String(255))

    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    linkedin_url: Mapped[str | None] = mapped_column(String(512))
    profile_url: Mapped[str | None] = mapped_column(String(512))

    email: Mapped[str | None] = mapped_column(String(320), index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    role: Mapped[PersonRole] = mapped_column(
        Enum(PersonRole, native_enum=False, length=16),
        default=PersonRole.UNKNOWN,
        nullable=False,
    )
    email_source: Mapped[EmailSource] = mapped_column(
        Enum(EmailSource, native_enum=False, length=16),
        default=EmailSource.UNKNOWN,
        nullable=False,
    )

    # Provenance: which discovery provider produced/last-updated this record.
    source: Mapped[str | None] = mapped_column(String(64))

    company: Mapped[Company] = relationship(back_populates="people")
