"""Resume parsing API routes (Module 2)."""

from __future__ import annotations

from fastapi import APIRouter, File, Query, UploadFile

from careerpilot.backend.api.dependencies import ResumeServiceDep
from careerpilot.backend.schemas.resume import ParsedResume, ResumeParseResult

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/parse", response_model=ParsedResume)
async def parse_resume(
    service: ResumeServiceDep,
    file: UploadFile = File(..., description="Resume file (.pdf or .txt)"),
) -> ParsedResume:
    """Parse an uploaded resume and return structured data (no persistence)."""
    data = await file.read()
    return service.parse_bytes(data, file.filename or "resume.pdf")


@router.post("/parse-into-profile", response_model=ResumeParseResult)
async def parse_into_profile(
    service: ResumeServiceDep,
    profile_id: int = Query(..., ge=1),
    file: UploadFile = File(..., description="Resume file (.pdf or .txt)"),
) -> ResumeParseResult:
    """Parse an uploaded resume and merge it into an existing profile."""
    data = await file.read()
    parsed = service.parse_bytes(data, file.filename or "resume.pdf")
    await service.apply_to_profile(parsed, profile_id, resume_path=file.filename)
    return ResumeParseResult(parsed=parsed, profile_id=profile_id, applied=True)
