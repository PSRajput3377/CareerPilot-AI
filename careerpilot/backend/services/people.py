"""People service (Module 5 — People Discovery).

Orchestrates: load a company → run a people-discovery provider → upsert the
discovered recruiters/employees into the database (idempotent on
``external_id``) so they are persisted, de-duplicated, and available to
downstream outreach modules.

Honors the orchestration contract: providers surface only public information,
discovered emails are stored unverified (verification is Module 7), and nothing
is ever auto-sent here.
"""

from __future__ import annotations

from careerpilot.backend.core.exceptions import NotFoundError
from careerpilot.backend.core.logging import get_logger
from careerpilot.backend.models.person import Person
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.person import PersonRepository
from careerpilot.backend.schemas.person import (
    PeopleSearchQuery,
    PersonCreate,
    PersonUpdate,
)
from careerpilot.backend.services.career_page.base import CompanyLike
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.people_discovery.base import (
    PeopleDiscoveryProvider,
    get_provider,
)

logger = get_logger("services.people")


class PeopleService:
    """Discover, persist, and manage people at companies."""

    def __init__(
        self,
        company_repo: CompanyRepository,
        person_repo: PersonRepository,
        provider: PeopleDiscoveryProvider | None = None,
    ) -> None:
        self._companies = CompanyService(company_repo)
        self._people = person_repo
        self._provider = provider or get_provider()

    @property
    def provider_name(self) -> str:
        """Identifier of the active discovery provider (for result provenance)."""
        return self._provider.name

    # -- Discovery --------------------------------------------------------- #

    async def discover_for_company(
        self, company_id: int, query: PeopleSearchQuery | None = None
    ) -> tuple[list[Person], int]:
        """Discover people for a stored company and upsert them.

        Returns the persisted people for the company (after the upsert) and the
        number of records inserted/updated this run.
        """
        query = query or PeopleSearchQuery()
        company = await self._companies.get(company_id)

        candidates = await self._provider.discover(
            CompanyLike(
                name=company.name,
                website=company.website,
                career_page=company.career_page,
                hiring_platform=company.hiring_platform,
                domain=company.domain,
            ),
            query,
        )

        saved = 0
        for candidate in candidates:
            await self._upsert(company_id, candidate)
            saved += 1

        people = await self._people.list_for_company(
            company_id,
            role=query.role,
            title=query.title,
            department=query.department,
            limit=query.limit,
        )
        logger.info(
            "Discovery via '%s' for company id=%s yielded %d people (%d persisted)",
            self._provider.name,
            company_id,
            len(people),
            saved,
        )
        return people, saved

    async def list_for_company(
        self, company_id: int, query: PeopleSearchQuery | None = None
    ) -> list[Person]:
        """Return stored people for a company (404 if the company is missing)."""
        query = query or PeopleSearchQuery()
        await self._companies.get(company_id)  # 404 if missing
        return await self._people.list_for_company(
            company_id,
            role=query.role,
            title=query.title,
            department=query.department,
            limit=query.limit,
        )

    # -- CRUD -------------------------------------------------------------- #

    async def get(self, person_id: int) -> Person:
        person = await self._people.get(person_id)
        if person is None:
            raise NotFoundError(f"Person {person_id} not found")
        return person

    async def update(self, person_id: int, payload: PersonUpdate) -> Person:
        person = await self.get(person_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(person, field, value)
        updated = await self._people.add(person)
        logger.info("Updated person id=%s", updated.id)
        return updated

    async def delete(self, person_id: int) -> None:
        person = await self.get(person_id)
        await self._people.delete(person)
        logger.info("Deleted person id=%s", person_id)

    # -- internals --------------------------------------------------------- #

    async def _upsert(self, company_id: int, payload: PersonCreate) -> Person:
        """Insert a discovered person, or update the existing match in place.

        Matching is by ``external_id`` within the company. Only fills/refreshes
        fields the provider supplied, never blanking existing data with ``None``.
        """
        existing: Person | None = None
        if payload.external_id:
            existing = await self._people.get_by_external_id(
                company_id, payload.external_id
            )

        if existing is None:
            return await self._people.add(_to_model(company_id, payload))

        incoming = payload.model_dump()
        for field, value in incoming.items():
            if value is None or value == "":
                continue
            # Discovery never verifies; don't downgrade an already-verified email.
            if field == "email_verified" and not value:
                continue
            setattr(existing, field, value)
        return await self._people.add(existing)


def _to_model(company_id: int, payload: PersonCreate) -> Person:
    return Person(
        company_id=company_id,
        external_id=payload.external_id,
        full_name=payload.full_name,
        title=payload.title,
        department=payload.department,
        location=payload.location,
        linkedin_url=payload.linkedin_url,
        profile_url=payload.profile_url,
        email=payload.email,
        email_verified=payload.email_verified,
        role=payload.role,
        email_source=payload.email_source,
        source=payload.source,
    )
