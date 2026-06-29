"""Repository for application-tracking persistence (Module 13)."""

from __future__ import annotations

from sqlalchemy import select

from careerpilot.backend.models.application import Application, ApplicationStatus
from careerpilot.backend.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    """Data-access for :class:`Application` (and its events via cascade)."""

    model = Application

    async def get_for_target(
        self, profile_id: int, company_id: int, job_listing_id: int | None
    ) -> Application | None:
        """Find an existing application for a (profile, company, role) target."""
        stmt = select(Application).where(
            Application.profile_id == profile_id,
            Application.company_id == company_id,
            Application.job_listing_id.is_(job_listing_id)
            if job_listing_id is None
            else Application.job_listing_id == job_listing_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_for_profile(
        self,
        profile_id: int,
        *,
        status: ApplicationStatus | None = None,
        company_id: int | None = None,
        limit: int = 100,
    ) -> list[Application]:
        """Applications for a profile, newest first, optionally filtered."""
        stmt = select(Application).where(Application.profile_id == profile_id)
        if status is not None:
            stmt = stmt.where(Application.status == status)
        if company_id is not None:
            stmt = stmt.where(Application.company_id == company_id)
        stmt = stmt.order_by(Application.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
