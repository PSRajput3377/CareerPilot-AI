"""Repository for job-match persistence and querying (Module 8)."""

from __future__ import annotations

from sqlalchemy import select

from careerpilot.backend.models.job_listing import JobListing
from careerpilot.backend.models.job_match import JobMatch
from careerpilot.backend.repositories.base import BaseRepository


class JobMatchRepository(BaseRepository[JobMatch]):
    """Data-access for :class:`JobMatch`."""

    model = JobMatch

    async def get_for_pair(
        self, profile_id: int, job_listing_id: int
    ) -> JobMatch | None:
        stmt = select(JobMatch).where(
            JobMatch.profile_id == profile_id,
            JobMatch.job_listing_id == job_listing_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_for_profile(
        self, profile_id: int, *, limit: int = 100
    ) -> list[JobMatch]:
        """Matches for a profile, highest score first."""
        stmt = (
            select(JobMatch)
            .where(JobMatch.profile_id == profile_id)
            .order_by(JobMatch.score.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_profile_company(
        self, profile_id: int, company_id: int, *, limit: int = 100
    ) -> list[JobMatch]:
        """Matches for a profile restricted to one company, highest score first."""
        stmt = (
            select(JobMatch)
            .join(JobListing, JobMatch.job_listing_id == JobListing.id)
            .where(
                JobMatch.profile_id == profile_id,
                JobListing.company_id == company_id,
            )
            .order_by(JobMatch.score.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
