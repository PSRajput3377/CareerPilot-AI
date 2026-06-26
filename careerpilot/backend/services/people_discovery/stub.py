"""Offline stub people-discovery provider (Module 5).

Returns deterministic recruiters and employees for a company. A small curated
dataset covers the well-known companies from Company Discovery (Module 3); for
any other company the provider synthesizes a plausible, clearly-marked roster so
the outreach pipeline can be exercised end-to-end without any external API.

Design notes honoring the orchestration contract:

* Emails are only attached when a deterministic *public* pattern can be derived
  from the company domain (``first.last@domain``); these are marked
  ``email_source=PUBLIC`` but **left unverified** — verification is Module 7.
* When no domain is known, people are returned without an email; pattern-based
  guessing belongs to Module 6, not here.
"""

from __future__ import annotations

import re

from careerpilot.backend.models.person import EmailSource, PersonRole
from careerpilot.backend.schemas.person import PeopleSearchQuery, PersonCreate
from careerpilot.backend.services.career_page.base import CompanyLike
from careerpilot.backend.services.people_discovery.base import PeopleDiscoveryProvider

# Curated public people per company domain. Kept small and illustrative.
_DATASET: dict[str, list[dict]] = {
    "stripe.com": [
        {
            "external_id": "stripe-1",
            "full_name": "Maya Chen",
            "title": "Technical Recruiter",
            "department": "Talent",
            "role": PersonRole.RECRUITER,
        },
        {
            "external_id": "stripe-2",
            "full_name": "David Okafor",
            "title": "Engineering Manager, Payments",
            "department": "Engineering",
            "role": PersonRole.HIRING_MANAGER,
        },
    ],
    "anthropic.com": [
        {
            "external_id": "anthropic-1",
            "full_name": "Priya Nair",
            "title": "Recruiting Lead",
            "department": "People",
            "role": PersonRole.RECRUITER,
        },
        {
            "external_id": "anthropic-2",
            "full_name": "Sam Rivera",
            "title": "Member of Technical Staff",
            "department": "Engineering",
            "role": PersonRole.ENGINEER,
        },
    ],
}

# Generic roster synthesized for companies absent from the curated dataset.
_SYNTH_TEMPLATE: list[dict] = [
    {"full_name": "Jordan Smith", "title": "Technical Recruiter", "role": PersonRole.RECRUITER},
    {
        "full_name": "Alex Johnson",
        "title": "Engineering Manager",
        "role": PersonRole.HIRING_MANAGER,
    },
    {"full_name": "Taylor Lee", "title": "Senior Software Engineer", "role": PersonRole.ENGINEER},
]


class StubPeopleProvider(PeopleDiscoveryProvider):
    """Deterministic offline provider backed by a curated dataset."""

    name = "stub"

    async def discover(
        self, company: CompanyLike, query: PeopleSearchQuery
    ) -> list[PersonCreate]:
        domain = (company.domain or "").lower()
        synthesized = domain not in _DATASET

        rows = _DATASET.get(domain) or self._synthesize(company.name)
        people = [self._to_create(company, row, synthesized) for row in rows]

        filtered = [p for p in people if self._matches(p, query)]
        return filtered[: query.limit]

    # -- internals --------------------------------------------------------- #

    def _matches(self, person: PersonCreate, q: PeopleSearchQuery) -> bool:
        if q.role is not None and person.role != q.role:
            return False
        if q.title and (not person.title or q.title.lower() not in person.title.lower()):
            return False
        if q.department and (
            not person.department or q.department.lower() not in person.department.lower()
        ):
            return False
        return True

    def _synthesize(self, company_name: str) -> list[dict]:
        slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-") or "company"
        rows: list[dict] = []
        for i, base in enumerate(_SYNTH_TEMPLATE, start=1):
            row = dict(base)
            row["external_id"] = f"{slug}-{i}"
            rows.append(row)
        return rows

    def _to_create(
        self, company: CompanyLike, row: dict, synthesized: bool
    ) -> PersonCreate:
        data = dict(row)
        email, email_source = self._derive_email(company, data["full_name"])
        return PersonCreate(
            external_id=data.get("external_id"),
            full_name=data["full_name"],
            title=data.get("title"),
            department=data.get("department"),
            role=data.get("role", PersonRole.UNKNOWN),
            email=email,
            email_source=email_source,
            email_verified=False,
            source="stub:synthesized" if synthesized else self.name,
        )

    def _derive_email(
        self, company: CompanyLike, full_name: str
    ) -> tuple[str | None, EmailSource]:
        """Build a deterministic ``first.last@domain`` address when a domain exists.

        Marked PUBLIC but never verified — verification is Module 7's job.
        """
        domain = (company.domain or "").lower()
        if not domain:
            return None, EmailSource.UNKNOWN
        parts = [re.sub(r"[^a-z]", "", p.lower()) for p in full_name.split()]
        parts = [p for p in parts if p]
        if len(parts) < 2:
            return None, EmailSource.UNKNOWN
        local = f"{parts[0]}.{parts[-1]}"
        return f"{local}@{domain}", EmailSource.PUBLIC
