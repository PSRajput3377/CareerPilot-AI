"""Schemas for the Application Tracker (Module 13)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from careerpilot.backend.models.application import ApplicationStatus


class ApplicationCreate(BaseModel):
    """Inputs to start tracking an application.

    Tracking the same (profile, company, job_listing) again returns the existing
    application rather than creating a duplicate.
    """

    company_id: int
    job_listing_id: int | None = Field(
        default=None, description="Target a specific role; omit for company-general"
    )
    status: ApplicationStatus = ApplicationStatus.SAVED
    notes: str | None = None


class ApplicationStatusUpdate(BaseModel):
    """Advance an application to a new status, optionally with a note."""

    status: ApplicationStatus
    note: str | None = None


class ApplicationNote(BaseModel):
    """Append a note to an application's timeline without changing status."""

    note: str = Field(min_length=1)


class ApplicationEventRead(BaseModel):
    """A persisted timeline entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    from_status: ApplicationStatus | None = None
    to_status: ApplicationStatus
    note: str | None = None
    created_at: datetime


class ApplicationRead(BaseModel):
    """A persisted application with its event timeline."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: int
    company_id: int
    job_listing_id: int | None = None
    status: ApplicationStatus
    notes: str | None = None
    events: list[ApplicationEventRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
