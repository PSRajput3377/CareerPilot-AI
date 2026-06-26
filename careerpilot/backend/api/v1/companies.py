"""Company Discovery API routes (Module 3)."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from careerpilot.backend.api.dependencies import CareerPageServiceDep, CompanyServiceDep
from careerpilot.backend.models.company import FundingStage, HiringStatus
from careerpilot.backend.schemas.company import (
    CompanyCreate,
    CompanyRead,
    CompanySearchQuery,
    CompanyUpdate,
)
from careerpilot.backend.schemas.job_listing import CareerPageResult, JobListingRead

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("/discover", response_model=list[CompanyRead])
async def discover_companies(
    query: CompanySearchQuery, service: CompanyServiceDep
) -> list[CompanyRead]:
    """Discover companies via the configured provider and persist them."""
    companies = await service.discover(query)
    return [CompanyRead.model_validate(c) for c in companies]


@router.get("/search", response_model=list[CompanyRead])
async def search_companies(
    service: CompanyServiceDep,
    name: str | None = None,
    industry: str | None = None,
    location: str | None = None,
    remote: bool | None = None,
    funding_stage: FundingStage | None = None,
    hiring_status: HiringStatus | None = None,
    limit: int = Query(20, ge=1, le=100),
) -> list[CompanyRead]:
    """Search companies already stored in the database."""
    query = CompanySearchQuery(
        name=name,
        industry=industry,
        location=location,
        remote=remote,
        funding_stage=funding_stage,
        hiring_status=hiring_status,
        limit=limit,
    )
    companies = await service.search_db(query)
    return [CompanyRead.model_validate(c) for c in companies]


@router.post("/{company_id}/detect-career-page", response_model=CareerPageResult)
async def detect_career_page(
    company_id: int, service: CareerPageServiceDep
) -> CareerPageResult:
    """Detect a company's ATS platform and extract public job listings (Module 4)."""
    return await service.detect_for_company(company_id)


@router.get("/{company_id}/jobs", response_model=list[JobListingRead])
async def list_company_jobs(
    company_id: int, service: CareerPageServiceDep
) -> list[JobListingRead]:
    """List stored job listings for a company."""
    jobs = await service.list_jobs(company_id)
    return [JobListingRead.model_validate(j) for j in jobs]


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(payload: CompanyCreate, service: CompanyServiceDep) -> CompanyRead:
    """Manually create a company."""
    company = await service.create(payload)
    return CompanyRead.model_validate(company)


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(company_id: int, service: CompanyServiceDep) -> CompanyRead:
    company = await service.get(company_id)
    return CompanyRead.model_validate(company)


@router.patch("/{company_id}", response_model=CompanyRead)
async def update_company(
    company_id: int, payload: CompanyUpdate, service: CompanyServiceDep
) -> CompanyRead:
    company = await service.update(company_id, payload)
    return CompanyRead.model_validate(company)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(company_id: int, service: CompanyServiceDep) -> None:
    await service.delete(company_id)
