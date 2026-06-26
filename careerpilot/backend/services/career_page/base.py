"""Career page detector interface and registry (Module 4).

A detector inspects what is known about a company (career-page URL, hiring
platform slug, website) and identifies the ATS plus any public job listings.

Two detector flavors are anticipated:

* **pattern** (ships now): offline, deterministic. Recognizes the ATS from URL
  signatures and known hiring-platform slugs; pulls listings from an optional
  injected fixture. No network — fully testable.
* **http** (future): fetches the career page and parses ATS embed scripts / JSON
  APIs via httpx + BeautifulSoup. Registers here without changing callers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from careerpilot.backend.schemas.job_listing import CareerPageDetection


class CompanyLike:
    """Minimal structural view a detector needs from a company.

    Using a tiny protocol-ish holder keeps detectors decoupled from the ORM.
    """

    def __init__(
        self,
        name: str,
        website: str | None = None,
        career_page: str | None = None,
        hiring_platform: str | None = None,
        domain: str | None = None,
    ) -> None:
        self.name = name
        self.website = website
        self.career_page = career_page
        self.hiring_platform = hiring_platform
        self.domain = domain


class CareerPageDetector(ABC):
    """Abstract base for career-page / ATS detectors."""

    name: str = "abstract"

    @abstractmethod
    async def detect(self, company: CompanyLike) -> CareerPageDetection:
        """Detect the ATS platform and listings for a company."""
        raise NotImplementedError


def get_detector(name: str | None = None) -> CareerPageDetector:
    """Return a detector by name, defaulting to the offline pattern detector."""
    from careerpilot.backend.services.career_page.pattern import PatternCareerPageDetector

    requested = (name or "pattern").lower()
    if requested in {"pattern", "default", "offline"}:
        return PatternCareerPageDetector()
    # Future: "http" detector for live fetching.
    return PatternCareerPageDetector()
