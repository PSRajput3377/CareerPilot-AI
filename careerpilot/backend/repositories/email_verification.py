"""Repository for email-verification persistence (Module 7)."""

from __future__ import annotations

from sqlalchemy import select

from careerpilot.backend.models.email_verification import EmailVerification
from careerpilot.backend.repositories.base import BaseRepository


class EmailVerificationRepository(BaseRepository[EmailVerification]):
    """Data-access for :class:`EmailVerification`."""

    model = EmailVerification

    async def list_for_person(self, person_id: int) -> list[EmailVerification]:
        stmt = (
            select(EmailVerification)
            .where(EmailVerification.person_id == person_id)
            .order_by(EmailVerification.email)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_person_email(
        self, person_id: int, email: str
    ) -> EmailVerification | None:
        stmt = select(EmailVerification).where(
            EmailVerification.person_id == person_id,
            EmailVerification.email == email,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
