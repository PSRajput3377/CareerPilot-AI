"""FastAPI dependency-injection wiring.

Each provider builds a repository over the request-scoped session and injects it
into the matching service, keeping construction in one place.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from careerpilot.backend.database.session import get_db
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.services.career_page import CareerPageService
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.resume import ResumeService
from careerpilot.backend.services.user_profile import UserProfileService

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_user_profile_service(session: DbSession) -> UserProfileService:
    return UserProfileService(UserProfileRepository(session))


UserProfileServiceDep = Annotated[UserProfileService, Depends(get_user_profile_service)]


def get_resume_service(session: DbSession) -> ResumeService:
    return ResumeService(UserProfileService(UserProfileRepository(session)))


ResumeServiceDep = Annotated[ResumeService, Depends(get_resume_service)]


def get_company_service(session: DbSession) -> CompanyService:
    return CompanyService(CompanyRepository(session))


CompanyServiceDep = Annotated[CompanyService, Depends(get_company_service)]


def get_career_page_service(session: DbSession) -> CareerPageService:
    return CareerPageService(CompanyRepository(session), JobListingRepository(session))


CareerPageServiceDep = Annotated[CareerPageService, Depends(get_career_page_service)]
