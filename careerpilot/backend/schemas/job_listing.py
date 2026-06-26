"""Schemas for Career Page Detection and job listings (Module 4)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from careerpilot.backend.models.job_listing import ATSPlatform


class JobListingCreate(BaseModel):
    """A job listing produced by a detector (provider-agnostic)."""

    external_id: str | None = Field(default=None, max_length=255)
    title: str = Field(min_length=1, max_length=512)
    location: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=64)
    url: str | None = Field(default=None, max_length=1024)
    description: str | None = None
    remote: bool | None = None


class JobListingRead(JobListingCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime


class CareerPageDetection(BaseModel):
    """Result of detecting a company's ATS / career page."""

    platform: ATSPlatform = ATSPlatform.UNKNOWN
    career_page: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    detector: str = "unknown"
    listings: list[JobListingCreate] = Field(default_factory=list)


class CareerPageResult(BaseModel):
    """API response combining detection + what was persisted."""

    company_id: int
    detection: CareerPageDetection
    listings_saved: int = 0
