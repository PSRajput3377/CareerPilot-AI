"""Application tracking ORM models (Module 13 — Application Tracker).

Tracks the lifecycle of a job application a :class:`UserProfile` (Module 1) is
pursuing at a :class:`Company` (Module 3), optionally tied to a specific
:class:`JobListing` (Module 4). Each application carries a :class:`ApplicationStatus`
that advances through a small state machine, and an append-only timeline of
:class:`ApplicationEvent` rows recording every status change and note — so the
history of an outreach is auditable and downstream modules (scheduler, analytics,
follow-ups) have something concrete to read.

One application per (profile, company, job_listing): re-tracking the same target
returns the existing row rather than duplicating.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from careerpilot.backend.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from careerpilot.backend.models.company import Company
    from careerpilot.backend.models.job_listing import JobListing
    from careerpilot.backend.models.user_profile import UserProfile


class ApplicationStatus(enum.StrEnum):
    """Lifecycle stage of a tracked application.

    Ordered roughly by progression; ``ACCEPTED``, ``REJECTED`` and ``WITHDRAWN``
    are terminal (see :data:`ALLOWED_TRANSITIONS`).
    """

    SAVED = "saved"  # interested, not yet applied
    APPLIED = "applied"  # application submitted
    OUTREACH_SENT = "outreach_sent"  # reached out to a person at the company
    REPLIED = "replied"  # got a response
    INTERVIEWING = "interviewing"  # in an interview loop
    OFFER = "offer"  # received an offer
    ACCEPTED = "accepted"  # accepted the offer (terminal)
    REJECTED = "rejected"  # turned down / closed (terminal)
    WITHDRAWN = "withdrawn"  # candidate stepped away (terminal)


#: Terminal statuses cannot transition further.
TERMINAL_STATUSES: frozenset[ApplicationStatus] = frozenset(
    {
        ApplicationStatus.ACCEPTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }
)

#: Allowed status transitions. A target can always be abandoned (rejected/
#: withdrawn) from any non-terminal state; otherwise progression is forward.
ALLOWED_TRANSITIONS: dict[ApplicationStatus, frozenset[ApplicationStatus]] = {
    ApplicationStatus.SAVED: frozenset(
        {
            ApplicationStatus.APPLIED,
            ApplicationStatus.OUTREACH_SENT,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.APPLIED: frozenset(
        {
            ApplicationStatus.OUTREACH_SENT,
            ApplicationStatus.REPLIED,
            ApplicationStatus.INTERVIEWING,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.OUTREACH_SENT: frozenset(
        {
            ApplicationStatus.APPLIED,
            ApplicationStatus.REPLIED,
            ApplicationStatus.INTERVIEWING,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.REPLIED: frozenset(
        {
            ApplicationStatus.INTERVIEWING,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.INTERVIEWING: frozenset(
        {
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.OFFER: frozenset(
        {
            ApplicationStatus.ACCEPTED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    # Terminal states have no outgoing transitions.
    ApplicationStatus.ACCEPTED: frozenset(),
    ApplicationStatus.REJECTED: frozenset(),
    ApplicationStatus.WITHDRAWN: frozenset(),
}


class Application(Base, TimestampMixin):
    """A tracked job application and its current lifecycle status."""

    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "company_id",
            "job_listing_id",
            name="uq_application_profile_company_listing",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    # Optional: an application may target a specific role or be company-general.
    job_listing_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_listings.id", ondelete="SET NULL"), index=True
    )

    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, native_enum=False, length=20),
        default=ApplicationStatus.SAVED,
        nullable=False,
        index=True,
    )
    #: Free-form note about the application as a whole (latest summary).
    notes: Mapped[str | None] = mapped_column(Text)

    profile: Mapped[UserProfile] = relationship()
    company: Mapped[Company] = relationship()
    job_listing: Mapped[JobListing | None] = relationship()
    events: Mapped[list[ApplicationEvent]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ApplicationEvent.id",
    )


class ApplicationEvent(Base, TimestampMixin):
    """An append-only timeline entry for an application.

    Records a status change (``from_status`` → ``to_status``) and/or a note.
    A plain note (no status change) leaves both status fields equal.
    """

    __tablename__ = "application_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )

    from_status: Mapped[ApplicationStatus | None] = mapped_column(
        Enum(ApplicationStatus, native_enum=False, length=20)
    )
    to_status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, native_enum=False, length=20), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)

    application: Mapped[Application] = relationship(back_populates="events")
