"""Career Page Detection service (Module 4).

Orchestrates: load a company → detect its ATS/career page → persist the detected
platform back onto the company → upsert any extracted job listings. Idempotent:
re-running updates existing listings (matched by external id) instead of
duplicating them.
"""

from __future__ import annotations

from careerpilot.backend.core.logging import get_logger
from careerpilot.backend.models.job_listing import ATSPlatform, JobListing
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.schemas.job_listing import (
    CareerPageDetection,
    CareerPageResult,
    JobListingCreate,
)
from careerpilot.backend.services.career_page.base import (
    CareerPageDetector,
    CompanyLike,
    get_detector,
)
from careerpilot.backend.services.company import CompanyService

logger = get_logger("services.career_page")


class CareerPageService:
    """Detect ATS platforms and extract job listings for companies."""

    def __init__(
        self,
        company_repo: CompanyRepository,
        listing_repo: JobListingRepository,
        detector: CareerPageDetector | None = None,
    ) -> None:
        self._companies = CompanyService(company_repo)
        self._company_repo = company_repo
        self._listings = listing_repo
        self._detector = detector or get_detector()

    async def detect_for_company(self, company_id: int) -> CareerPageResult:
        """Detect and persist ATS + listings for a stored company."""
        company = await self._companies.get(company_id)

        detection = await self._detector.detect(
            CompanyLike(
                name=company.name,
                website=company.website,
                career_page=company.career_page,
                hiring_platform=company.hiring_platform,
                domain=company.domain,
            )
        )

        # Persist detected platform onto the company.
        company.ats_platform = detection.platform.value
        if detection.platform not in (ATSPlatform.UNKNOWN, ATSPlatform.CUSTOM):
            # Normalize the raw hiring_platform slug to the detected platform.
            company.hiring_platform = detection.platform.value
        if detection.career_page and not company.career_page:
            company.career_page = detection.career_page
        await self._company_repo.add(company)

        saved = await self._upsert_listings(company_id, detection.listings)
        logger.info(
            "Detected ATS '%s' (conf=%.2f) for company id=%s; %d listings saved",
            detection.platform.value,
            detection.confidence,
            company_id,
            saved,
        )
        return CareerPageResult(
            company_id=company_id, detection=detection, listings_saved=saved
        )

    async def list_jobs(self, company_id: int) -> list[JobListing]:
        """Return stored job listings for a company."""
        await self._companies.get(company_id)  # 404 if missing
        return await self._listings.list_for_company(company_id)

    async def _upsert_listings(
        self, company_id: int, listings: list[JobListingCreate]
    ) -> int:
        count = 0
        for item in listings:
            existing = None
            if item.external_id:
                existing = await self._listings.get_by_external_id(
                    company_id, item.external_id
                )
            if existing is None:
                await self._listings.add(_to_model(company_id, item))
            else:
                for field, value in item.model_dump(exclude_unset=True).items():
                    setattr(existing, field, value)
                await self._listings.add(existing)
            count += 1
        return count


def _to_model(company_id: int, item: JobListingCreate) -> JobListing:
    return JobListing(
        company_id=company_id,
        external_id=item.external_id,
        title=item.title,
        location=item.location,
        department=item.department,
        employment_type=item.employment_type,
        url=item.url,
        description=item.description,
        remote=item.remote,
    )


def detection_summary(detection: CareerPageDetection) -> str:
    """Human-readable one-line summary (used by the CLI)."""
    return (
        f"{detection.platform.value} "
        f"(confidence {detection.confidence:.0%}, detector {detection.detector})"
    )
