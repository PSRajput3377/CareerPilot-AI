"""Offline stub company discovery provider (Module 3).

Returns deterministic results from a small curated dataset of well-known
companies (public information). This makes the discovery pipeline fully testable
and usable without any external API. Real providers replace it via the registry.

When the query names a company not in the dataset, the provider synthesizes a
plausible record (guessing the domain) so the rest of the pipeline can proceed —
clearly marked with ``source="stub:synthesized"``.
"""

from __future__ import annotations

import re

from careerpilot.backend.models.company import FundingStage, HiringStatus
from careerpilot.backend.schemas.company import CompanyCreate, CompanySearchQuery
from careerpilot.backend.services.company_discovery.base import CompanyDiscoveryProvider

# Curated public dataset. Kept small and factual; extend freely.
_DATASET: list[dict] = [
    {
        "name": "Stripe",
        "website": "https://stripe.com",
        "domain": "stripe.com",
        "career_page": "https://stripe.com/jobs",
        "linkedin_url": "https://www.linkedin.com/company/stripe",
        "industry": "Fintech",
        "location": "San Francisco, CA",
        "remote_friendly": True,
        "employee_count": 8000,
        "tech_stack": ["Ruby", "Go", "Scala", "React", "AWS"],
        "hiring_platform": "greenhouse",
        "funding_stage": FundingStage.LATE_STAGE,
        "hiring_status": HiringStatus.HIRING,
    },
    {
        "name": "Datadog",
        "website": "https://www.datadoghq.com",
        "domain": "datadoghq.com",
        "career_page": "https://careers.datadoghq.com",
        "linkedin_url": "https://www.linkedin.com/company/datadog",
        "industry": "Observability",
        "location": "New York, NY",
        "remote_friendly": True,
        "employee_count": 5000,
        "tech_stack": ["Go", "Python", "Java", "Kubernetes", "Kafka"],
        "hiring_platform": "greenhouse",
        "funding_stage": FundingStage.PUBLIC,
        "hiring_status": HiringStatus.HIRING,
    },
    {
        "name": "Vercel",
        "website": "https://vercel.com",
        "domain": "vercel.com",
        "career_page": "https://vercel.com/careers",
        "linkedin_url": "https://www.linkedin.com/company/vercel",
        "industry": "Developer Tools",
        "location": "Remote",
        "remote_friendly": True,
        "employee_count": 600,
        "tech_stack": ["TypeScript", "Next.js", "React", "Rust", "AWS"],
        "hiring_platform": "ashby",
        "funding_stage": FundingStage.LATE_STAGE,
        "hiring_status": HiringStatus.HIRING,
    },
    {
        "name": "Notion",
        "website": "https://www.notion.so",
        "domain": "notion.so",
        "career_page": "https://www.notion.so/careers",
        "linkedin_url": "https://www.linkedin.com/company/notionhq",
        "industry": "Productivity",
        "location": "San Francisco, CA",
        "remote_friendly": True,
        "employee_count": 800,
        "tech_stack": ["TypeScript", "React", "Node.js", "PostgreSQL"],
        "hiring_platform": "greenhouse",
        "funding_stage": FundingStage.SERIES_C,
        "hiring_status": HiringStatus.HIRING,
    },
    {
        "name": "Anthropic",
        "website": "https://www.anthropic.com",
        "domain": "anthropic.com",
        "career_page": "https://www.anthropic.com/careers",
        "linkedin_url": "https://www.linkedin.com/company/anthropicresearch",
        "industry": "Artificial Intelligence",
        "location": "San Francisco, CA",
        "remote_friendly": True,
        "employee_count": 1000,
        "tech_stack": ["Python", "PyTorch", "Kubernetes", "GCP"],
        "hiring_platform": "greenhouse",
        "funding_stage": FundingStage.LATE_STAGE,
        "hiring_status": HiringStatus.HIRING,
    },
]


class StubCompanyProvider(CompanyDiscoveryProvider):
    """Deterministic offline provider backed by a curated dataset."""

    name = "stub"

    async def discover(self, query: CompanySearchQuery) -> list[CompanyCreate]:
        matches = [row for row in _DATASET if self._matches(row, query)]

        # If a specific name was requested but not found, synthesize a record.
        if query.name and not any(
            query.name.lower() in row["name"].lower() for row in matches
        ):
            synthesized = self._synthesize(query.name)
            if synthesized is not None:
                matches.append(synthesized)

        results = [self._to_create(row) for row in matches[: query.limit]]
        return results

    # -- internals --------------------------------------------------------- #

    def _matches(self, row: dict, q: CompanySearchQuery) -> bool:
        if q.name and q.name.lower() not in row["name"].lower():
            return False
        if q.industry and q.industry.lower() not in row["industry"].lower():
            return False
        if q.location and not (
            q.location.lower() in row["location"].lower()
            or (q.remote and row.get("remote_friendly"))
        ):
            return False
        if q.remote is not None and bool(row.get("remote_friendly")) != q.remote:
            # Only enforce when location didn't already account for remote.
            if not (q.location and q.remote):
                return False
        if q.funding_stage is not None and row["funding_stage"] != q.funding_stage:
            return False
        if q.hiring_status is not None and row["hiring_status"] != q.hiring_status:
            return False
        return True

    def _to_create(self, row: dict) -> CompanyCreate:
        data = dict(row)
        data.setdefault("source", self.name)
        return CompanyCreate(**data)

    def _synthesize(self, name: str) -> CompanyCreate | None:
        slug = re.sub(r"[^a-z0-9]+", "", name.lower())
        if not slug:
            return None
        domain = f"{slug}.com"
        return CompanyCreate(
            name=name.strip(),
            website=f"https://{domain}",
            domain=domain,
            funding_stage=FundingStage.UNKNOWN,
            hiring_status=HiringStatus.UNKNOWN,
            source="stub:synthesized",
        )
