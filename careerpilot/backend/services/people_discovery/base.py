"""People discovery provider interface and registry (Module 5).

A provider turns a company plus a search query into candidate :class:`PersonCreate`
records (recruiters and employees) from some data source. The offline stub
provider ships now (deterministic, no network); real providers (public APIs,
scraping via Playwright/BeautifulSoup) register later without changing the
service or callers.

Following the orchestration contract, providers only surface publicly available
information and prefer verified public emails; they never fabricate a
deliverable address. Email *pattern* guessing is a separate module (Module 6).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from careerpilot.backend.schemas.person import PeopleSearchQuery, PersonCreate
from careerpilot.backend.services.career_page.base import CompanyLike


class PeopleDiscoveryProvider(ABC):
    """Abstract base for people discovery providers."""

    #: Stable identifier recorded as ``source`` provenance on results.
    name: str = "abstract"

    @abstractmethod
    async def discover(
        self, company: CompanyLike, query: PeopleSearchQuery
    ) -> list[PersonCreate]:
        """Return candidate people at the company matching the query."""
        raise NotImplementedError


def get_provider(name: str | None = None) -> PeopleDiscoveryProvider:
    """Return a people discovery provider by name, defaulting to the offline stub.

    Unknown names fall back to the stub so discovery always works offline and in
    tests.
    """
    from careerpilot.backend.services.people_discovery.stub import StubPeopleProvider

    requested = (name or "stub").lower()
    if requested in {"stub", "default", "offline", "sample"}:
        return StubPeopleProvider()
    # Real providers (e.g. "linkedin", "hunter", "scrape") slot in here.
    return StubPeopleProvider()
