"""Repository for job-listing persistence (Module 4)."""

from __future__ import annotations

from sqlalchemy import select

from careerpilot.backend.models.job_listing import JobListing
from careerpilot.backend.repositories.base import BaseRepository


class JobListingRepository(BaseRepository[JobListing]):
    """Data-access for :class:`JobListing`."""

    model = JobListing

    async def list_for_company(self, company_id: int) -> list[JobListing]:
        stmt = (
            select(JobListing)
            .where(JobListing.company_id == company_id)
            .order_by(JobListing.title)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_external_id(
        self, company_id: int, external_id: str
    ) -> JobListing | None:
        stmt = select(JobListing).where(
            JobListing.company_id == company_id,
            JobListing.external_id == external_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
