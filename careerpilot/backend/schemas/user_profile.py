"""Pydantic schemas for the User Profile module (Module 1).

These define the API contract (request/response) and are decoupled from the ORM
models. ``*Create`` schemas are inputs; ``*Read`` schemas are outputs built from
ORM rows via ``model_validate`` (``from_attributes``).
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator

from careerpilot.backend.models.user_profile import WorkAuthorization

# --------------------------------------------------------------------------- #
# Skills
# --------------------------------------------------------------------------- #


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    proficiency: str | None = Field(default=None, max_length=32)
    years: float | None = Field(default=None, ge=0, le=80)


class SkillRead(SkillCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --------------------------------------------------------------------------- #
# Experience
# --------------------------------------------------------------------------- #


class ExperienceCreate(BaseModel):
    company: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    is_internship: bool = False

    @model_validator(mode="after")
    def _check_dates(self) -> ExperienceCreate:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class ExperienceRead(ExperienceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --------------------------------------------------------------------------- #
# Education
# --------------------------------------------------------------------------- #


class EducationCreate(BaseModel):
    institution: str = Field(min_length=1, max_length=255)
    degree: str | None = Field(default=None, max_length=255)
    field_of_study: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    grade: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def _check_dates(self) -> EducationCreate:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class EducationRead(EducationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --------------------------------------------------------------------------- #
# Projects & achievements (populated by Module 2)
# --------------------------------------------------------------------------- #


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None
    tech_stack: str | None = None
    url: str | None = None


class AchievementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    description: str


# --------------------------------------------------------------------------- #
# Profile
# --------------------------------------------------------------------------- #


class UserProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    resume_path: str | None = Field(default=None, max_length=1024)
    github_url: HttpUrl | None = None
    portfolio_url: HttpUrl | None = None
    linkedin_url: HttpUrl | None = None
    preferred_role: str | None = Field(default=None, max_length=255)
    preferred_location: str | None = Field(default=None, max_length=255)
    work_authorization: WorkAuthorization | None = None
    preferred_companies: list[str] = Field(default_factory=list)
    preferred_salary_min: int | None = Field(default=None, ge=0)
    preferred_salary_max: int | None = Field(default=None, ge=0)
    availability: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _check_salary(self) -> UserProfileBase:
        lo, hi = self.preferred_salary_min, self.preferred_salary_max
        if lo is not None and hi is not None and hi < lo:
            raise ValueError("preferred_salary_max cannot be below preferred_salary_min")
        return self


class UserProfileCreate(UserProfileBase):
    skills: list[SkillCreate] = Field(default_factory=list)
    experiences: list[ExperienceCreate] = Field(default_factory=list)
    educations: list[EducationCreate] = Field(default_factory=list)


class UserProfileUpdate(BaseModel):
    """Partial update — every field optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    resume_path: str | None = Field(default=None, max_length=1024)
    github_url: HttpUrl | None = None
    portfolio_url: HttpUrl | None = None
    linkedin_url: HttpUrl | None = None
    preferred_role: str | None = Field(default=None, max_length=255)
    preferred_location: str | None = Field(default=None, max_length=255)
    work_authorization: WorkAuthorization | None = None
    preferred_companies: list[str] | None = None
    preferred_salary_min: int | None = Field(default=None, ge=0)
    preferred_salary_max: int | None = Field(default=None, ge=0)
    availability: str | None = Field(default=None, max_length=255)


class UserProfileRead(UserProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    skills: list[SkillRead] = Field(default_factory=list)
    experiences: list[ExperienceRead] = Field(default_factory=list)
    educations: list[EducationRead] = Field(default_factory=list)
    projects: list[ProjectRead] = Field(default_factory=list)
    achievements: list[AchievementRead] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_companies(cls, data: object) -> object:
        """Convert the stored comma-separated string into a list on read."""
        # When validating from an ORM object, preferred_companies is a string.
        raw = getattr(data, "preferred_companies", None)
        if isinstance(raw, str):
            companies = [c.strip() for c in raw.split(",") if c.strip()]
            # Build a shallow dict view preserving ORM attributes.
            return _ORMView(data, {"preferred_companies": companies})
        return data


class _ORMView:
    """Attribute proxy that overrides selected fields of an ORM object.

    Lets ``from_attributes`` validation read most fields off the ORM row while
    substituting a transformed value for ``preferred_companies``.
    """

    def __init__(self, wrapped: object, overrides: dict[str, object]) -> None:
        self._wrapped = wrapped
        self._overrides = overrides

    def __getattr__(self, item: str) -> object:
        if item in self._overrides:
            return self._overrides[item]
        return getattr(self._wrapped, item)
