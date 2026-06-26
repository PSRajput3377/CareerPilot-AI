"""Pydantic schemas for Company Discovery (Module 3)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from careerpilot.backend.models.company import FundingStage, HiringStatus


def _split_csv(value: object) -> list[str]:
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


class CompanySearchQuery(BaseModel):
    """Filters for discovering companies (Module 3)."""

    name: str | None = Field(default=None, description="Company name or keyword")
    industry: str | None = None
    location: str | None = None
    remote: bool | None = None
    funding_stage: FundingStage | None = None
    hiring_status: HiringStatus | None = None
    limit: int = Field(default=20, ge=1, le=100)


class CompanyBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=512)
    domain: str | None = Field(default=None, max_length=255)
    career_page: str | None = Field(default=None, max_length=512)
    linkedin_url: str | None = Field(default=None, max_length=512)
    industry: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    remote_friendly: bool | None = None
    employee_count: int | None = Field(default=None, ge=0)
    tech_stack: list[str] = Field(default_factory=list)
    hiring_platform: str | None = Field(default=None, max_length=64)
    ats_platform: str | None = Field(default=None, max_length=32)
    funding_stage: FundingStage = FundingStage.UNKNOWN
    hiring_status: HiringStatus = HiringStatus.UNKNOWN
    source: str | None = Field(default=None, max_length=64)


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    """Partial update — all fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=512)
    domain: str | None = Field(default=None, max_length=255)
    career_page: str | None = Field(default=None, max_length=512)
    linkedin_url: str | None = Field(default=None, max_length=512)
    industry: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    remote_friendly: bool | None = None
    employee_count: int | None = Field(default=None, ge=0)
    tech_stack: list[str] | None = None
    hiring_platform: str | None = Field(default=None, max_length=64)
    funding_stage: FundingStage | None = None
    hiring_status: HiringStatus | None = None


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _coerce_tech_stack(cls, data: object) -> object:
        """Turn the stored comma-separated tech_stack string into a list."""
        raw = getattr(data, "tech_stack", None)
        if isinstance(raw, str):
            return _CompanyView(data, {"tech_stack": _split_csv(raw)})
        return data


class _CompanyView:
    """Attribute proxy overriding selected fields of an ORM Company on read."""

    def __init__(self, wrapped: object, overrides: dict[str, object]) -> None:
        self._wrapped = wrapped
        self._overrides = overrides

    def __getattr__(self, item: str) -> object:
        if item in self._overrides:
            return self._overrides[item]
        return getattr(self._wrapped, item)
