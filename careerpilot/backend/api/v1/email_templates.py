"""Email Template Engine API routes (Module 10).

CRUD for templates (built-ins are read-only) plus a render endpoint that
resolves a context into placeholder values and substitutes them.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from careerpilot.backend.api.dependencies import EmailTemplateServiceDep
from careerpilot.backend.models.email_template import TemplateCategory
from careerpilot.backend.schemas.email_template import (
    EmailTemplateCreate,
    EmailTemplateRead,
    EmailTemplateUpdate,
    RenderContext,
    RenderedEmail,
)

router = APIRouter(prefix="/email-templates", tags=["email-templates"])


@router.get("", response_model=list[EmailTemplateRead])
async def list_templates(
    service: EmailTemplateServiceDep,
    category: TemplateCategory | None = None,
    limit: int = Query(100, ge=1, le=200),
) -> list[EmailTemplateRead]:
    """List templates (built-ins are auto-seeded), optionally filtered."""
    templates = await service.list(category=category, limit=limit)
    return [EmailTemplateRead.model_validate(t) for t in templates]


@router.post("", response_model=EmailTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: EmailTemplateCreate, service: EmailTemplateServiceDep
) -> EmailTemplateRead:
    template = await service.create(payload)
    return EmailTemplateRead.model_validate(template)


@router.get("/{template_id}", response_model=EmailTemplateRead)
async def get_template(
    template_id: int, service: EmailTemplateServiceDep
) -> EmailTemplateRead:
    template = await service.get(template_id)
    return EmailTemplateRead.model_validate(template)


@router.patch("/{template_id}", response_model=EmailTemplateRead)
async def update_template(
    template_id: int, payload: EmailTemplateUpdate, service: EmailTemplateServiceDep
) -> EmailTemplateRead:
    template = await service.update(template_id, payload)
    return EmailTemplateRead.model_validate(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int, service: EmailTemplateServiceDep
) -> None:
    await service.delete(template_id)


@router.post("/{template_id}/render", response_model=RenderedEmail)
async def render_template_endpoint(
    template_id: int, ctx: RenderContext, service: EmailTemplateServiceDep
) -> RenderedEmail:
    """Render a template against a resolved context (no send)."""
    return await service.render(template_id, ctx)
