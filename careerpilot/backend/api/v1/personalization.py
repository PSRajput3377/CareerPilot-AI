"""AI Personalization Engine API routes (Module 12).

Compose a personalized outreach draft by tying together the profile, recipient,
target company/role, overlapping skills, an optional base template, and the best
subject line. Stateless — the draft is returned for review, never sent.
"""

from __future__ import annotations

from fastapi import APIRouter

from careerpilot.backend.api.dependencies import PersonalizationServiceDep
from careerpilot.backend.schemas.personalization import (
    PersonalizationRequest,
    PersonalizedEmail,
)

router = APIRouter(tags=["personalization"])


@router.post("/personalize", response_model=PersonalizedEmail)
async def personalize_email(
    request: PersonalizationRequest, service: PersonalizationServiceDep
) -> PersonalizedEmail:
    """Compose a personalized outreach draft for the given context."""
    return await service.personalize(request)
