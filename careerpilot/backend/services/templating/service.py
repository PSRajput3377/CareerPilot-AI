"""Email Template service (Module 10).

CRUD for templates (built-ins are read-only) plus rendering: resolve a context
(candidate, company, recipient person, role) into placeholder values and
substitute them. Rendering never sends — it produces reviewable subject/body
text consumed by personalization (Module 12) and sending (Module 15).
"""

from __future__ import annotations

from careerpilot.backend.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from careerpilot.backend.core.logging import get_logger
from careerpilot.backend.models.email_template import (
    EmailTemplate,
    TemplateCategory,
)
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.email_template import EmailTemplateRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.person import PersonRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.email_template import (
    EmailTemplateCreate,
    EmailTemplateUpdate,
    RenderContext,
    RenderedEmail,
)
from careerpilot.backend.services.templating.builtins import BUILTIN_TEMPLATES
from careerpilot.backend.services.templating.renderer import render_template

logger = get_logger("services.templating")


class EmailTemplateService:
    """Manage and render email templates."""

    def __init__(
        self,
        template_repo: EmailTemplateRepository,
        profile_repo: UserProfileRepository,
        company_repo: CompanyRepository,
        person_repo: PersonRepository,
        listing_repo: JobListingRepository,
    ) -> None:
        self._templates = template_repo
        self._profiles = profile_repo
        self._companies = company_repo
        self._people = person_repo
        self._listings = listing_repo

    # -- seeding ----------------------------------------------------------- #

    async def seed_builtins(self) -> int:
        """Insert any missing built-in templates. Idempotent. Returns count added."""
        added = 0
        for spec in BUILTIN_TEMPLATES:
            if await self._templates.get_by_name(spec.name) is None:
                await self._templates.add(_to_model(spec, is_builtin=True))
                added += 1
        if added:
            logger.info("Seeded %d built-in email templates", added)
        return added

    # -- CRUD -------------------------------------------------------------- #

    async def create(self, payload: EmailTemplateCreate) -> EmailTemplate:
        if await self._templates.get_by_name(payload.name) is not None:
            raise ConflictError(f"Template '{payload.name}' already exists")
        created = await self._templates.add(_to_model(payload, is_builtin=False))
        logger.info("Created email template id=%s name=%s", created.id, created.name)
        return created

    async def get(self, template_id: int) -> EmailTemplate:
        template = await self._templates.get(template_id)
        if template is None:
            raise NotFoundError(f"Email template {template_id} not found")
        return template

    async def list(
        self, *, category: TemplateCategory | None = None, limit: int = 100
    ) -> list[EmailTemplate]:
        # Ensure built-ins exist so a fresh DB still lists something useful.
        await self.seed_builtins()
        return await self._templates.list_templates(category=category, limit=limit)

    async def update(
        self, template_id: int, payload: EmailTemplateUpdate
    ) -> EmailTemplate:
        template = await self.get(template_id)
        if template.is_builtin:
            raise ValidationError("Built-in templates cannot be edited")
        data = payload.model_dump(exclude_unset=True)
        if "name" in data and data["name"] != template.name:
            if await self._templates.get_by_name(data["name"]) is not None:
                raise ConflictError(f"Template '{data['name']}' already exists")
        for field, value in data.items():
            setattr(template, field, value)
        updated = await self._templates.add(template)
        logger.info("Updated email template id=%s", updated.id)
        return updated

    async def delete(self, template_id: int) -> None:
        template = await self.get(template_id)
        if template.is_builtin:
            raise ValidationError("Built-in templates cannot be deleted")
        await self._templates.delete(template)
        logger.info("Deleted email template id=%s", template_id)

    # -- rendering --------------------------------------------------------- #

    async def render(self, template_id: int, ctx: RenderContext) -> RenderedEmail:
        """Render a template against a resolved context."""
        template = await self.get(template_id)
        values = await self._resolve_values(ctx)

        subject, missing_subj = render_template(template.subject_template, values)
        body, missing_body = render_template(template.body_template, values)

        missing = list(dict.fromkeys(missing_subj + missing_body))
        return RenderedEmail(
            template_id=template.id,
            template_name=template.name,
            subject=subject,
            body=body,
            missing_placeholders=missing,
        )

    async def _resolve_values(self, ctx: RenderContext) -> dict[str, str]:
        """Build the placeholder dictionary from the context's referenced rows."""
        values: dict[str, str] = {}

        profile = await self._profiles.get(ctx.profile_id)
        if profile is None:
            raise NotFoundError(f"User profile {ctx.profile_id} not found")
        values["candidate_name"] = profile.name
        if profile.preferred_role:
            values["candidate_role"] = profile.preferred_role

        if ctx.company_id is not None:
            company = await self._companies.get(ctx.company_id)
            if company is None:
                raise NotFoundError(f"Company {ctx.company_id} not found")
            values["company"] = company.name
            if company.industry:
                values["industry"] = company.industry

        if ctx.person_id is not None:
            person = await self._people.get(ctx.person_id)
            if person is None:
                raise NotFoundError(f"Person {ctx.person_id} not found")
            first, last = _split_name(person.full_name)
            values["full_name"] = person.full_name
            values["first_name"] = first
            if last:
                values["last_name"] = last

        if ctx.job_listing_id is not None:
            listing = await self._listings.get(ctx.job_listing_id)
            if listing is None:
                raise NotFoundError(f"Job listing {ctx.job_listing_id} not found")
            values["role"] = listing.title

        # Fall back to the candidate's preferred role for {role} when no listing.
        values.setdefault("role", profile.preferred_role or "")
        # Ad-hoc extras win.
        values.update({k: v for k, v in ctx.extra.items() if v})
        return {k: v for k, v in values.items() if v}


def _to_model(payload: EmailTemplateCreate, *, is_builtin: bool) -> EmailTemplate:
    return EmailTemplate(
        name=payload.name,
        category=payload.category,
        subject_template=payload.subject_template,
        body_template=payload.body_template,
        description=payload.description,
        is_builtin=is_builtin,
    )


def _split_name(full_name: str) -> tuple[str, str]:
    parts = [p for p in full_name.split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]
