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
from careerpilot.backend.repositories.cover_letter import CoverLetterRepository
from careerpilot.backend.repositories.email_verification import (
    EmailVerificationRepository,
)
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.job_match import JobMatchRepository
from careerpilot.backend.repositories.person import PersonRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.services.career_page import CareerPageService
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.cover_letter import CoverLetterService
from careerpilot.backend.services.email_pattern import EmailPatternService
from careerpilot.backend.services.email_verification import EmailVerificationService
from careerpilot.backend.services.job_matching import JobMatchingService
from careerpilot.backend.services.people import PeopleService
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


def get_people_service(session: DbSession) -> PeopleService:
    return PeopleService(CompanyRepository(session), PersonRepository(session))


PeopleServiceDep = Annotated[PeopleService, Depends(get_people_service)]


def get_email_pattern_service(session: DbSession) -> EmailPatternService:
    return EmailPatternService(CompanyRepository(session), PersonRepository(session))


EmailPatternServiceDep = Annotated[
    EmailPatternService, Depends(get_email_pattern_service)
]


def get_email_verification_service(session: DbSession) -> EmailVerificationService:
    return EmailVerificationService(
        CompanyRepository(session),
        PersonRepository(session),
        EmailVerificationRepository(session),
    )


EmailVerificationServiceDep = Annotated[
    EmailVerificationService, Depends(get_email_verification_service)
]


def get_job_matching_service(session: DbSession) -> JobMatchingService:
    return JobMatchingService(
        UserProfileRepository(session),
        CompanyRepository(session),
        JobListingRepository(session),
        JobMatchRepository(session),
    )


JobMatchingServiceDep = Annotated[
    JobMatchingService, Depends(get_job_matching_service)
]


def get_cover_letter_service(session: DbSession) -> CoverLetterService:
    return CoverLetterService(
        UserProfileRepository(session),
        CompanyRepository(session),
        JobListingRepository(session),
        CoverLetterRepository(session),
        JobMatchRepository(session),
    )


CoverLetterServiceDep = Annotated[
    CoverLetterService, Depends(get_cover_letter_service)
]
