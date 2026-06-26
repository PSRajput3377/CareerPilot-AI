"""Pydantic schemas for People Discovery (Module 5)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from careerpilot.backend.models.person import EmailSource, PersonRole


class PeopleSearchQuery(BaseModel):
    """Filters for discovering people at a company (Module 5)."""

    role: PersonRole | None = Field(
        default=None, description="Restrict to a role, e.g. recruiter"
    )
    title: str | None = Field(
        default=None, description="Title keyword, e.g. 'engineering manager'"
    )
    department: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class PersonCreate(BaseModel):
    """A person produced by a discovery provider (provider-agnostic)."""

    external_id: str | None = Field(default=None, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    linkedin_url: str | None = Field(default=None, max_length=512)
    profile_url: str | None = Field(default=None, max_length=512)
    email: str | None = Field(default=None, max_length=320)
    email_verified: bool = False
    role: PersonRole = PersonRole.UNKNOWN
    email_source: EmailSource = EmailSource.UNKNOWN
    source: str | None = Field(default=None, max_length=64)


class PersonUpdate(BaseModel):
    """Partial update — all fields optional."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    linkedin_url: str | None = Field(default=None, max_length=512)
    profile_url: str | None = Field(default=None, max_length=512)
    email: str | None = Field(default=None, max_length=320)
    email_verified: bool | None = None
    role: PersonRole | None = None
    email_source: EmailSource | None = None


class PersonRead(PersonCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime


class PeopleDiscoveryResult(BaseModel):
    """API response combining discovery + what was persisted."""

    company_id: int
    provider: str = "unknown"
    people: list[PersonRead] = Field(default_factory=list)
    people_saved: int = 0
