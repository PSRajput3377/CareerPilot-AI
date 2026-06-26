"""Generic async repository (Repository Pattern).

Encapsulates persistence for a single ORM model so services depend on this
abstraction rather than SQLAlchemy directly. Feature repositories subclass this
and add query methods specific to their aggregate.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from careerpilot.backend.database.base import Base


class BaseRepository[ModelT: Base]:
    """CRUD operations shared by all repositories."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, entity: ModelT) -> ModelT:
        """Persist a new entity and flush to populate its primary key."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def get(self, entity_id: int) -> ModelT | None:
        """Fetch by primary key, or ``None`` if absent."""
        return await self.session.get(self.model, entity_id)

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[ModelT]:
        """Return a page of entities ordered by primary key."""
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Total number of rows for this model."""
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def delete(self, entity: ModelT) -> None:
        """Remove an entity from the session."""
        await self.session.delete(entity)
        await self.session.flush()
