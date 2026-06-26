"""Company service (Module 3).

Business operations for companies plus the discovery orchestration: run a query
through a discovery provider, then upsert results into the database so they are
persisted, de-duplicated, and available to downstream modules.
"""

from __future__ import annotations

from careerpilot.backend.core.exceptions import ConflictError, NotFoundError
from careerpilot.backend.core.logging import get_logger
from careerpilot.backend.models.company import Company
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.schemas.company import (
    CompanyCreate,
    CompanySearchQuery,
    CompanyUpdate,
)
from careerpilot.backend.services.company_discovery.base import (
    CompanyDiscoveryProvider,
    get_provider,
)

logger = get_logger("services.company")


class CompanyService:
    """CRUD, search, and discovery for companies."""

    def __init__(
        self,
        repository: CompanyRepository,
        provider: CompanyDiscoveryProvider | None = None,
    ) -> None:
        self._repo = repository
        self._provider = provider or get_provider()

    # -- CRUD -------------------------------------------------------------- #

    async def create(self, payload: CompanyCreate) -> Company:
        existing = await self._repo.get_by_name(payload.name)
        if existing is not None:
            raise ConflictError(f"Company '{payload.name}' already exists")
        company = _to_model(payload)
        created = await self._repo.add(company)
        logger.info("Created company id=%s name=%s", created.id, created.name)
        return created

    async def get(self, company_id: int) -> Company:
        company = await self._repo.get(company_id)
        if company is None:
            raise NotFoundError(f"Company {company_id} not found")
        return company

    async def update(self, company_id: int, payload: CompanyUpdate) -> Company:
        company = await self.get(company_id)
        data = payload.model_dump(exclude_unset=True)
        if "tech_stack" in data and data["tech_stack"] is not None:
            data["tech_stack"] = _join(data["tech_stack"])
        for field, value in data.items():
            setattr(company, field, value)
        updated = await self._repo.add(company)
        logger.info("Updated company id=%s", updated.id)
        return updated

    async def delete(self, company_id: int) -> None:
        company = await self.get(company_id)
        await self._repo.delete(company)
        logger.info("Deleted company id=%s", company_id)

    async def search_db(self, query: CompanySearchQuery) -> list[Company]:
        """Search only companies already stored in the database."""
        return await self._repo.search(
            name=query.name,
            industry=query.industry,
            location=query.location,
            remote=query.remote,
            funding_stage=query.funding_stage,
            hiring_status=query.hiring_status,
            limit=query.limit,
        )

    # -- Discovery --------------------------------------------------------- #

    async def discover(self, query: CompanySearchQuery) -> list[Company]:
        """Discover companies via the provider and upsert them into the DB.

        Returns the persisted records (existing rows are updated in place, new
        ones inserted), so callers always get database-backed entities.
        """
        candidates = await self._provider.discover(query)
        persisted: list[Company] = []
        for candidate in candidates:
            persisted.append(await self._upsert(candidate))
        logger.info(
            "Discovery via '%s' for query name=%r yielded %d companies",
            self._provider.name,
            query.name,
            len(persisted),
        )
        return persisted

    async def _upsert(self, payload: CompanyCreate) -> Company:
        """Insert a discovered company, or update the existing match in place.

        Matching prefers domain, then name. Only fills/refreshes fields that the
        provider supplied, never blanking curated data with ``None``.
        """
        existing: Company | None = None
        if payload.domain:
            existing = await self._repo.get_by_domain(payload.domain)
        if existing is None:
            existing = await self._repo.get_by_name(payload.name)

        if existing is None:
            return await self._repo.add(_to_model(payload))

        incoming = payload.model_dump()
        for field, value in incoming.items():
            if value is None or value == [] or value == "":
                continue
            if field == "tech_stack":
                value = _join(value)
            setattr(existing, field, value)
        return await self._repo.add(existing)


def _to_model(payload: CompanyCreate) -> Company:
    return Company(
        name=payload.name,
        website=payload.website,
        domain=payload.domain,
        career_page=payload.career_page,
        linkedin_url=payload.linkedin_url,
        industry=payload.industry,
        location=payload.location,
        remote_friendly=payload.remote_friendly,
        employee_count=payload.employee_count,
        tech_stack=_join(payload.tech_stack),
        hiring_platform=payload.hiring_platform,
        funding_stage=payload.funding_stage,
        hiring_status=payload.hiring_status,
        source=payload.source,
    )


def _join(items: list[str]) -> str:
    return ", ".join(s.strip() for s in items if s and s.strip())
