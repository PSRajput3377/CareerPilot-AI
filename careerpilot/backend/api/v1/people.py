"""People Discovery API routes (Module 5).

People are discovered and listed in the context of a company, then managed
individually. Discovery and company-scoped listing live under
``/companies/{company_id}/people``; single-person reads/updates/deletes live
under ``/people/{person_id}``.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from careerpilot.backend.api.dependencies import PeopleServiceDep
from careerpilot.backend.models.person import PersonRole
from careerpilot.backend.schemas.person import (
    PeopleDiscoveryResult,
    PeopleSearchQuery,
    PersonRead,
    PersonUpdate,
)

router = APIRouter(tags=["people"])


@router.post(
    "/companies/{company_id}/people/discover", response_model=PeopleDiscoveryResult
)
async def discover_people(
    company_id: int,
    service: PeopleServiceDep,
    query: PeopleSearchQuery | None = None,
) -> PeopleDiscoveryResult:
    """Discover recruiters/employees at a company and persist them (Module 5)."""
    people, saved = await service.discover_for_company(company_id, query)
    return PeopleDiscoveryResult(
        company_id=company_id,
        provider=service.provider_name,
        people=[PersonRead.model_validate(p) for p in people],
        people_saved=saved,
    )


@router.get("/companies/{company_id}/people", response_model=list[PersonRead])
async def list_company_people(
    company_id: int,
    service: PeopleServiceDep,
    role: PersonRole | None = None,
    title: str | None = None,
    department: str | None = None,
    limit: int = Query(20, ge=1, le=100),
) -> list[PersonRead]:
    """List stored people for a company."""
    query = PeopleSearchQuery(
        role=role, title=title, department=department, limit=limit
    )
    people = await service.list_for_company(company_id, query)
    return [PersonRead.model_validate(p) for p in people]


@router.get("/people/{person_id}", response_model=PersonRead)
async def get_person(person_id: int, service: PeopleServiceDep) -> PersonRead:
    person = await service.get(person_id)
    return PersonRead.model_validate(person)


@router.patch("/people/{person_id}", response_model=PersonRead)
async def update_person(
    person_id: int, payload: PersonUpdate, service: PeopleServiceDep
) -> PersonRead:
    person = await service.update(person_id, payload)
    return PersonRead.model_validate(person)


@router.delete("/people/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(person_id: int, service: PeopleServiceDep) -> None:
    await service.delete(person_id)
