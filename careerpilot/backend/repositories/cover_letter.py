"""Repository for cover-letter persistence (Module 9)."""

from __future__ import annotations

from sqlalchemy import select

from careerpilot.backend.models.cover_letter import CoverLetter
from careerpilot.backend.repositories.base import BaseRepository


class CoverLetterRepository(BaseRepository[CoverLetter]):
    """Data-access for :class:`CoverLetter`."""

    model = CoverLetter

    async def list_for_profile(
        self, profile_id: int, *, limit: int = 100
    ) -> list[CoverLetter]:
        """Cover letters for a profile, newest first."""
        stmt = (
            select(CoverLetter)
            .where(CoverLetter.profile_id == profile_id)
            .order_by(CoverLetter.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
