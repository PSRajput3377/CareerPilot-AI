"""Repository for email-template persistence (Module 10)."""

from __future__ import annotations

from sqlalchemy import select

from careerpilot.backend.models.email_template import EmailTemplate, TemplateCategory
from careerpilot.backend.repositories.base import BaseRepository


class EmailTemplateRepository(BaseRepository[EmailTemplate]):
    """Data-access for :class:`EmailTemplate`."""

    model = EmailTemplate

    async def get_by_name(self, name: str) -> EmailTemplate | None:
        stmt = select(EmailTemplate).where(EmailTemplate.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_templates(
        self, *, category: TemplateCategory | None = None, limit: int = 100
    ) -> list[EmailTemplate]:
        stmt = select(EmailTemplate)
        if category is not None:
            stmt = stmt.where(EmailTemplate.category == category)
        stmt = stmt.order_by(EmailTemplate.name).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
