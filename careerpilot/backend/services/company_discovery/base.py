"""Company discovery provider interface and registry (Module 3).

A provider turns a search query into candidate :class:`CompanyCreate` records
from some data source. The offline stub provider ships now (deterministic, no
network); real providers (public APIs, scraping via Playwright/BeautifulSoup)
register later without changing the service or callers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from careerpilot.backend.schemas.company import CompanyCreate, CompanySearchQuery


class CompanyDiscoveryProvider(ABC):
    """Abstract base for company discovery providers."""

    #: Stable identifier recorded as ``source`` provenance on results.
    name: str = "abstract"

    @abstractmethod
    async def discover(self, query: CompanySearchQuery) -> list[CompanyCreate]:
        """Return candidate companies matching the query."""
        raise NotImplementedError


def get_provider(name: str | None = None) -> CompanyDiscoveryProvider:
    """Return a discovery provider by name, defaulting to the offline stub.

    Unknown names fall back to the stub so discovery always works offline and in
    tests.
    """
    from careerpilot.backend.services.company_discovery.stub import StubCompanyProvider

    requested = (name or "stub").lower()
    if requested in {"stub", "default", "offline", "sample"}:
        return StubCompanyProvider()
    # Real providers (e.g. "clearbit", "scrape") slot in here as they are built.
    return StubCompanyProvider()
