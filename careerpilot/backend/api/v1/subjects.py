"""Subject Generator API routes (Module 11).

Generate ranked, varied email subject lines for an outreach context. Stateless —
nothing is persisted.
"""

from __future__ import annotations

from fastapi import APIRouter

from careerpilot.backend.api.dependencies import SubjectServiceDep
from careerpilot.backend.schemas.subject import SubjectRequest, SubjectResult

router = APIRouter(tags=["subjects"])


@router.post("/subjects/generate", response_model=SubjectResult)
async def generate_subjects(
    request: SubjectRequest, service: SubjectServiceDep
) -> SubjectResult:
    """Generate ranked subject lines for the given context."""
    return await service.generate(request)
