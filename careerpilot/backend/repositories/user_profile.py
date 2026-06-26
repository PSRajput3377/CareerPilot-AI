"""Repository for User Profile persistence (Module 1)."""

from __future__ import annotations

from sqlalchemy import func, select

from careerpilot.backend.models.user_profile import UserProfile
from careerpilot.backend.repositories.base import BaseRepository


class UserProfileRepository(BaseRepository[UserProfile]):
    """Data-access for :class:`UserProfile` and its children."""

    model = UserProfile

    async def get_by_email(self, email: str) -> UserProfile | None:
        """Look up a profile by its unique email (case-insensitive)."""
        stmt = select(UserProfile).where(func.lower(UserProfile.email) == email.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
