"""Repository for Person persistence and querying (Module 5)."""

from __future__ import annotations

from sqlalchemy import select

from careerpilot.backend.models.person import Person, PersonRole
from careerpilot.backend.repositories.base import BaseRepository


class PersonRepository(BaseRepository[Person]):
    """Data-access for :class:`Person`."""

    model = Person

    async def list_for_company(
        self,
        company_id: int,
        *,
        role: PersonRole | None = None,
        title: str | None = None,
        department: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Person]:
        """Filtered list of people at a company.

        Text filters are case-insensitive substring matches; the role filter is
        exact. Ordered by name for stable output.
        """
        stmt = select(Person).where(Person.company_id == company_id)
        if role is not None:
            stmt = stmt.where(Person.role == role)
        if title:
            stmt = stmt.where(Person.title.ilike(f"%{title}%"))
        if department:
            stmt = stmt.where(Person.department.ilike(f"%{department}%"))
        stmt = stmt.order_by(Person.full_name).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_external_id(
        self, company_id: int, external_id: str
    ) -> Person | None:
        stmt = select(Person).where(
            Person.company_id == company_id,
            Person.external_id == external_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
