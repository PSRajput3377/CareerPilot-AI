"""Email verification ORM model (Module 7 — Email Verification).

Records the outcome of checking whether a :class:`Person`'s email is likely
deliverable. This is the ``verify deliverability`` gate in the outreach pipeline:
a person's ``email_verified`` flag is only set true once a verification yields a
``valid`` status, and the orchestration contract forbids sending to anything
that has not passed this gate.

One row per (person, email): re-verifying the same address updates the existing
record (idempotent) rather than accumulating duplicates.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from careerpilot.backend.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from careerpilot.backend.models.person import Person


class VerificationStatus(enum.StrEnum):
    """Deliverability verdict for an email address."""

    #: Syntactically valid, domain accepts mail, not disposable — safe to use.
    VALID = "valid"
    #: Definitively undeliverable (bad syntax or non-mail domain).
    INVALID = "invalid"
    #: Deliverable-ish but discouraged (role account, disposable, catch-all).
    RISKY = "risky"
    #: Could not be determined (e.g. no email to check).
    UNKNOWN = "unknown"


class EmailVerification(Base, TimestampMixin):
    """The result of verifying a single email address for a person."""

    __tablename__ = "email_verifications"
    __table_args__ = (
        UniqueConstraint("person_id", "email", name="uq_verification_person_email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), index=True
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, native_enum=False, length=16),
        default=VerificationStatus.UNKNOWN,
        nullable=False,
    )

    # Individual check outcomes (deterministic, offline).
    syntax_ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    domain_ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mx_found: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_disposable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_role_account: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    #: Confidence in the verdict, 0..1.
    confidence: Mapped[float] = mapped_column(default=0.0, nullable=False)
    #: Human-readable explanation of the verdict.
    reason: Mapped[str | None] = mapped_column(Text)
    #: Which verifier produced this result.
    verifier: Mapped[str | None] = mapped_column(String(64))

    person: Mapped[Person] = relationship(back_populates="verifications")
