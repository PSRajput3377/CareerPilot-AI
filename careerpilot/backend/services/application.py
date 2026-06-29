"""Application Tracker service (Module 13).

Tracks the lifecycle of a job application: start tracking a target (profile +
company, optionally a specific role), advance its status through a guarded state
machine, append free-form notes, and read the full timeline. Every status change
and note is recorded as an append-only :class:`ApplicationEvent`, so the history
is auditable and feeds the scheduler, analytics, and follow-up modules.

This module records and organizes — it never sends anything. Status changes like
``OUTREACH_SENT`` reflect actions taken elsewhere (the explicit send step,
Module 15).
"""

from __future__ import annotations

from careerpilot.backend.core.exceptions import NotFoundError, ValidationError
from careerpilot.backend.core.logging import get_logger
from careerpilot.backend.models.application import (
    ALLOWED_TRANSITIONS,
    Application,
    ApplicationEvent,
    ApplicationStatus,
)
from careerpilot.backend.repositories.application import ApplicationRepository
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.application import (
    ApplicationCreate,
    ApplicationNote,
    ApplicationStatusUpdate,
)
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.user_profile import UserProfileService

logger = get_logger("services.application")


class ApplicationService:
    """Create, advance, annotate, and read tracked applications."""

    def __init__(
        self,
        profile_repo: UserProfileRepository,
        company_repo: CompanyRepository,
        listing_repo: JobListingRepository,
        application_repo: ApplicationRepository,
    ) -> None:
        self._profiles = UserProfileService(profile_repo)
        self._companies = CompanyService(company_repo)
        self._listings = listing_repo
        self._applications = application_repo

    # -- Tracking ---------------------------------------------------------- #

    async def track(
        self, profile_id: int, request: ApplicationCreate
    ) -> Application:
        """Start tracking an application (idempotent on the target).

        If an application already exists for the (profile, company, role) target,
        it is returned unchanged rather than duplicated.
        """
        await self._profiles.get(profile_id)  # 404 if missing
        company = await self._companies.get(request.company_id)
        await self._validate_listing(request.job_listing_id, company.id)

        existing = await self._applications.get_for_target(
            profile_id, company.id, request.job_listing_id
        )
        if existing is not None:
            logger.info(
                "Application already tracked id=%s (profile=%s company=%s listing=%s)",
                existing.id,
                profile_id,
                company.id,
                request.job_listing_id,
            )
            return existing

        application = Application(
            profile_id=profile_id,
            company_id=company.id,
            job_listing_id=request.job_listing_id,
            status=request.status,
            notes=request.notes,
        )
        # Seed the timeline with the initial status.
        application.events.append(
            ApplicationEvent(
                from_status=None,
                to_status=request.status,
                note=request.notes,
            )
        )
        saved = await self._applications.add(application)
        logger.info(
            "Tracking application id=%s status=%s (profile=%s company=%s)",
            saved.id,
            saved.status.value,
            profile_id,
            company.id,
        )
        return saved

    async def advance(
        self, application_id: int, update: ApplicationStatusUpdate
    ) -> Application:
        """Move an application to a new status, recording a timeline event.

        Raises :class:`ValidationError` if the transition is not allowed by the
        state machine. Re-asserting the current status is a no-op state-wise but
        still records a note when one is given.
        """
        application = await self.get(application_id)
        current = application.status
        target = update.status

        if target != current:
            allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
            if target not in allowed:
                raise ValidationError(
                    f"Cannot move application {application_id} from "
                    f"'{current.value}' to '{target.value}'. "
                    f"Allowed: {sorted(s.value for s in allowed) or 'none (terminal)'}."
                )

        application.events.append(
            ApplicationEvent(
                from_status=current,
                to_status=target,
                note=update.note,
            )
        )
        application.status = target
        saved = await self._applications.add(application)
        logger.info(
            "Application id=%s status %s -> %s",
            application_id,
            current.value,
            target.value,
        )
        return saved

    async def add_note(
        self, application_id: int, payload: ApplicationNote
    ) -> Application:
        """Append a note to the timeline without changing status."""
        application = await self.get(application_id)
        application.events.append(
            ApplicationEvent(
                from_status=application.status,
                to_status=application.status,
                note=payload.note,
            )
        )
        application.notes = payload.note
        saved = await self._applications.add(application)
        logger.info("Added note to application id=%s", application_id)
        return saved

    # -- Reads ------------------------------------------------------------- #

    async def get(self, application_id: int) -> Application:
        application = await self._applications.get(application_id)
        if application is None:
            raise NotFoundError(f"Application {application_id} not found")
        return application

    async def list_for_profile(
        self,
        profile_id: int,
        *,
        status: ApplicationStatus | None = None,
        company_id: int | None = None,
        limit: int = 100,
    ) -> list[Application]:
        await self._profiles.get(profile_id)  # 404 if missing
        return await self._applications.list_for_profile(
            profile_id, status=status, company_id=company_id, limit=limit
        )

    async def delete(self, application_id: int) -> None:
        application = await self.get(application_id)
        await self._applications.delete(application)
        logger.info("Deleted application id=%s", application_id)

    # -- internals --------------------------------------------------------- #

    async def _validate_listing(
        self, job_listing_id: int | None, company_id: int
    ) -> None:
        """Ensure a referenced job listing exists and belongs to the company."""
        if job_listing_id is None:
            return
        listing = await self._listings.get(job_listing_id)
        if listing is None or listing.company_id != company_id:
            raise NotFoundError(
                f"Job listing {job_listing_id} not found for company {company_id}"
            )
