"""Job Matching API routes (Module 8).

Score a profile against a company's job listings (or a single listing), persist
the scores, and list stored matches ranked by fit.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from careerpilot.backend.api.dependencies import JobMatchingServiceDep
from careerpilot.backend.schemas.job_match import JobMatchRead, JobMatchResult

router = APIRouter(tags=["job-matching"])


@router.post(
    "/profiles/{profile_id}/match/companies/{company_id}",
    response_model=list[JobMatchResult],
)
async def match_profile_to_company(
    profile_id: int, company_id: int, service: JobMatchingServiceDep
) -> list[JobMatchResult]:
    """Score a profile against every job listing at a company (ranked)."""
    return await service.match_company(profile_id, company_id)


@router.post(
    "/profiles/{profile_id}/match/jobs/{job_listing_id}",
    response_model=JobMatchResult,
)
async def match_profile_to_job(
    profile_id: int, job_listing_id: int, service: JobMatchingServiceDep
) -> JobMatchResult:
    """Score a profile against a single job listing."""
    return await service.match_listing(profile_id, job_listing_id)


@router.get("/profiles/{profile_id}/matches", response_model=list[JobMatchRead])
async def list_profile_matches(
    profile_id: int,
    service: JobMatchingServiceDep,
    company_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> list[JobMatchRead]:
    """List stored matches for a profile (optionally scoped to one company)."""
    matches = await service.list_matches(profile_id, company_id, limit=limit)
    return [JobMatchRead.model_validate(m) for m in matches]
