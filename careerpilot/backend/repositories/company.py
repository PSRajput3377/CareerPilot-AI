"""Repository for Company persistence and querying (Module 3)."""

from __future__ import annotations

from sqlalchemy import func, or_, select

from careerpilot.backend.models.company import Company, FundingStage, HiringStatus
from careerpilot.backend.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    """Data-access for :class:`Company`."""

    model = Company

    async def get_by_name(self, name: str) -> Company | None:
        stmt = select(Company).where(func.lower(Company.name) == name.lower())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_domain(self, domain: str) -> Company | None:
        stmt = select(Company).where(func.lower(Company.domain) == domain.lower())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def search(
        self,
        *,
        name: str | None = None,
        industry: str | None = None,
        location: str | None = None,
        remote: bool | None = None,
        funding_stage: FundingStage | None = None,
        hiring_status: HiringStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Company]:
        """Filtered search over stored companies.

        Text filters are case-insensitive substring matches; enum/bool filters
        are exact. Used by the service to return already-known companies before
        (and after) consulting external discovery providers.
        """
        stmt = select(Company)
        if name:
            stmt = stmt.where(Company.name.ilike(f"%{name}%"))
        if industry:
            stmt = stmt.where(Company.industry.ilike(f"%{industry}%"))
        if location:
            stmt = stmt.where(
                or_(
                    Company.location.ilike(f"%{location}%"),
                    Company.remote_friendly.is_(True),
                )
                if remote
                else Company.location.ilike(f"%{location}%")
            )
        if remote is not None and not location:
            stmt = stmt.where(Company.remote_friendly.is_(remote))
        if funding_stage is not None:
            stmt = stmt.where(Company.funding_stage == funding_stage)
        if hiring_status is not None:
            stmt = stmt.where(Company.hiring_status == hiring_status)

        stmt = stmt.order_by(Company.name).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
