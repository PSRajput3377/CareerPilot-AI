"""Offline URL-pattern career-page detector (Module 4).

Recognizes the ATS platform from URL signatures and known hiring-platform slugs.
This is real, useful detection that needs no network: most companies' career
pages embed their ATS in the hostname or path (e.g. ``boards.greenhouse.io/acme``,
``jobs.lever.co/acme``, ``acme.myworkdayjobs.com``).

Optionally seeds listings from a fixture map (``{slug_or_name: [listings]}``),
used by tests and demos to exercise the full extract-and-persist path without a
live ATS.
"""

from __future__ import annotations

import re

from careerpilot.backend.models.job_listing import ATSPlatform
from careerpilot.backend.schemas.job_listing import (
    CareerPageDetection,
    JobListingCreate,
)
from careerpilot.backend.services.career_page.base import (
    CareerPageDetector,
    CompanyLike,
)

# Ordered (platform, regex) signatures matched against URLs and slugs.
# Patterns are intentionally specific to avoid false positives.
_SIGNATURES: list[tuple[ATSPlatform, re.Pattern[str]]] = [
    (ATSPlatform.GREENHOUSE, re.compile(r"greenhouse\.io|boards\.greenhouse", re.I)),
    (ATSPlatform.LEVER, re.compile(r"lever\.co|jobs\.lever", re.I)),
    (ATSPlatform.ASHBY, re.compile(r"ashbyhq\.com|jobs\.ashby", re.I)),
    (ATSPlatform.WORKDAY, re.compile(r"myworkdayjobs\.com|workday", re.I)),
    (ATSPlatform.SMARTRECRUITERS, re.compile(r"smartrecruiters\.com", re.I)),
    (ATSPlatform.BAMBOOHR, re.compile(r"bamboohr\.com", re.I)),
    (ATSPlatform.JOBVITE, re.compile(r"jobvite\.com", re.I)),
    (ATSPlatform.ORACLE, re.compile(r"oraclecloud\.com|taleo\.net|oracle", re.I)),
    (
        ATSPlatform.SAP_SUCCESSFACTORS,
        re.compile(r"successfactors\.com|sapsf\.com|jobs\.sap", re.I),
    ),
]

# Hiring-platform slugs (e.g. set during discovery) map directly to a platform.
_SLUG_MAP: dict[str, ATSPlatform] = {
    "greenhouse": ATSPlatform.GREENHOUSE,
    "lever": ATSPlatform.LEVER,
    "ashby": ATSPlatform.ASHBY,
    "workday": ATSPlatform.WORKDAY,
    "smartrecruiters": ATSPlatform.SMARTRECRUITERS,
    "bamboohr": ATSPlatform.BAMBOOHR,
    "jobvite": ATSPlatform.JOBVITE,
    "oracle": ATSPlatform.ORACLE,
    "sap_successfactors": ATSPlatform.SAP_SUCCESSFACTORS,
    "successfactors": ATSPlatform.SAP_SUCCESSFACTORS,
}


class PatternCareerPageDetector(CareerPageDetector):
    """Deterministic ATS detection from URLs and slugs."""

    name = "pattern"

    def __init__(
        self, listings_fixture: dict[str, list[JobListingCreate]] | None = None
    ) -> None:
        # Maps a company name or hiring-platform slug to canned listings.
        self._fixture = listings_fixture or {}

    async def detect(self, company: CompanyLike) -> CareerPageDetection:
        platform, confidence = self._classify(company)
        listings = self._listings_for(company)
        return CareerPageDetection(
            platform=platform,
            career_page=company.career_page,
            confidence=confidence,
            detector=self.name,
            listings=listings,
        )

    # -- internals --------------------------------------------------------- #

    def _classify(self, company: CompanyLike) -> tuple[ATSPlatform, float]:
        # 1. Explicit hiring-platform slug is the strongest signal.
        slug = (company.hiring_platform or "").strip().lower()
        if slug in _SLUG_MAP:
            return _SLUG_MAP[slug], 0.95

        # 2. Match URL signatures.
        haystack = " ".join(
            filter(None, [company.career_page, company.website, company.domain])
        )
        for platform, pattern in _SIGNATURES:
            if pattern.search(haystack):
                return platform, 0.85

        # 3. A career page exists but matches no known ATS → custom page.
        if company.career_page:
            return ATSPlatform.CUSTOM, 0.5

        return ATSPlatform.UNKNOWN, 0.0

    def _listings_for(self, company: CompanyLike) -> list[JobListingCreate]:
        for key in (company.hiring_platform, company.name):
            if key and key in self._fixture:
                return list(self._fixture[key])
        return []
