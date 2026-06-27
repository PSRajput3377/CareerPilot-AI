"""Schemas for the Email Template Engine (Module 10)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from careerpilot.backend.models.email_template import TemplateCategory


class EmailTemplateCreate(BaseModel):
    """Inputs to create a template."""

    name: str = Field(min_length=1, max_length=128)
    category: TemplateCategory = TemplateCategory.OUTREACH
    subject_template: str = Field(min_length=1, max_length=512)
    body_template: str = Field(min_length=1)
    description: str | None = Field(default=None, max_length=512)


class EmailTemplateUpdate(BaseModel):
    """Partial update — all fields optional. Built-in templates reject updates."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    category: TemplateCategory | None = None
    subject_template: str | None = Field(default=None, min_length=1, max_length=512)
    body_template: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, max_length=512)


class EmailTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: TemplateCategory
    subject_template: str
    body_template: str
    description: str | None = None
    is_builtin: bool
    created_at: datetime
    updated_at: datetime


class RenderContext(BaseModel):
    """Identifiers used to build the placeholder values for rendering."""

    profile_id: int
    company_id: int | None = None
    person_id: int | None = None
    job_listing_id: int | None = None
    # Ad-hoc extra values, merged last (override resolved fields).
    extra: dict[str, str] = Field(default_factory=dict)


class RenderedEmail(BaseModel):
    """The result of rendering a template against a context."""

    template_id: int
    template_name: str
    subject: str
    body: str
    #: Placeholders present in the template but absent from the context.
    missing_placeholders: list[str] = Field(default_factory=list)
