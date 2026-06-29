"""Application Tracker API routes (Module 13).

Start tracking an application for a profile, advance its status through the
lifecycle state machine, append notes, and read the timeline. This module only
records the state of an outreach — it never sends anything.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from careerpilot.backend.api.dependencies import ApplicationServiceDep
from careerpilot.backend.models.application import ApplicationStatus
from careerpilot.backend.schemas.application import (
    ApplicationCreate,
    ApplicationNote,
    ApplicationRead,
    ApplicationStatusUpdate,
)

router = APIRouter(tags=["applications"])


@router.post(
    "/profiles/{profile_id}/applications",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
async def track_application(
    profile_id: int, request: ApplicationCreate, service: ApplicationServiceDep
) -> ApplicationRead:
    """Start tracking an application (idempotent on the target)."""
    application = await service.track(profile_id, request)
    return ApplicationRead.model_validate(application)


@router.get(
    "/profiles/{profile_id}/applications", response_model=list[ApplicationRead]
)
async def list_applications(
    profile_id: int,
    service: ApplicationServiceDep,
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    company_id: int | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
) -> list[ApplicationRead]:
    """List a profile's tracked applications (newest first)."""
    applications = await service.list_for_profile(
        profile_id, status=status_filter, company_id=company_id, limit=limit
    )
    return [ApplicationRead.model_validate(a) for a in applications]


@router.get("/applications/{application_id}", response_model=ApplicationRead)
async def get_application(
    application_id: int, service: ApplicationServiceDep
) -> ApplicationRead:
    application = await service.get(application_id)
    return ApplicationRead.model_validate(application)


@router.post(
    "/applications/{application_id}/status", response_model=ApplicationRead
)
async def advance_application(
    application_id: int,
    update: ApplicationStatusUpdate,
    service: ApplicationServiceDep,
) -> ApplicationRead:
    """Advance an application to a new status (validated by the state machine)."""
    application = await service.advance(application_id, update)
    return ApplicationRead.model_validate(application)


@router.post(
    "/applications/{application_id}/notes", response_model=ApplicationRead
)
async def add_application_note(
    application_id: int, payload: ApplicationNote, service: ApplicationServiceDep
) -> ApplicationRead:
    """Append a note to an application's timeline (no status change)."""
    application = await service.add_note(application_id, payload)
    return ApplicationRead.model_validate(application)


@router.delete(
    "/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_application(
    application_id: int, service: ApplicationServiceDep
) -> None:
    await service.delete(application_id)
