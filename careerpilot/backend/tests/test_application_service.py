"""Service tests for the Application Tracker (Module 13)."""

from __future__ import annotations

import pytest

from careerpilot.backend.core.exceptions import NotFoundError, ValidationError
from careerpilot.backend.models.application import ApplicationStatus
from careerpilot.backend.models.job_listing import JobListing
from careerpilot.backend.repositories.application import ApplicationRepository
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.application import (
    ApplicationCreate,
    ApplicationNote,
    ApplicationStatusUpdate,
)
from careerpilot.backend.schemas.company import CompanyCreate
from careerpilot.backend.schemas.user_profile import UserProfileCreate
from careerpilot.backend.services.application import ApplicationService
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.user_profile import UserProfileService


def _service(session) -> ApplicationService:
    return ApplicationService(
        UserProfileRepository(session),
        CompanyRepository(session),
        JobListingRepository(session),
        ApplicationRepository(session),
    )


async def _profile(session) -> int:
    service = UserProfileService(UserProfileRepository(session))
    profile = await service.create(
        UserProfileCreate(name="Jane Engineer", email="jane@example.com")
    )
    return profile.id


async def _company(session, name: str = "Stripe") -> int:
    service = CompanyService(CompanyRepository(session))
    company = await service.create(CompanyCreate(name=name))
    return company.id


async def _listing(session, company_id: int) -> int:
    repo = JobListingRepository(session)
    listing = await repo.add(
        JobListing(company_id=company_id, title="Backend Engineer")
    )
    return listing.id


async def test_track_creates_with_seed_event(session):
    pid = await _profile(session)
    cid = await _company(session)
    service = _service(session)

    app_obj = await service.track(pid, ApplicationCreate(company_id=cid))
    assert app_obj.status is ApplicationStatus.SAVED
    assert len(app_obj.events) == 1
    assert app_obj.events[0].from_status is None
    assert app_obj.events[0].to_status is ApplicationStatus.SAVED


async def test_track_is_idempotent_on_target(session):
    pid = await _profile(session)
    cid = await _company(session)
    service = _service(session)

    first = await service.track(pid, ApplicationCreate(company_id=cid))
    second = await service.track(pid, ApplicationCreate(company_id=cid))
    assert first.id == second.id
    # No duplicate event from the second track.
    assert len(second.events) == 1


async def test_track_distinct_listings_are_separate(session):
    pid = await _profile(session)
    cid = await _company(session)
    jid = await _listing(session, cid)
    service = _service(session)

    general = await service.track(pid, ApplicationCreate(company_id=cid))
    role = await service.track(
        pid, ApplicationCreate(company_id=cid, job_listing_id=jid)
    )
    assert general.id != role.id


async def test_advance_valid_transition_records_event(session):
    pid = await _profile(session)
    cid = await _company(session)
    service = _service(session)
    app_obj = await service.track(pid, ApplicationCreate(company_id=cid))

    advanced = await service.advance(
        app_obj.id,
        ApplicationStatusUpdate(status=ApplicationStatus.APPLIED, note="Submitted"),
    )
    assert advanced.status is ApplicationStatus.APPLIED
    assert len(advanced.events) == 2
    last = advanced.events[-1]
    assert last.from_status is ApplicationStatus.SAVED
    assert last.to_status is ApplicationStatus.APPLIED
    assert last.note == "Submitted"


async def test_advance_invalid_transition_raises(session):
    pid = await _profile(session)
    cid = await _company(session)
    service = _service(session)
    app_obj = await service.track(pid, ApplicationCreate(company_id=cid))

    # saved -> offer is not allowed.
    with pytest.raises(ValidationError):
        await service.advance(
            app_obj.id, ApplicationStatusUpdate(status=ApplicationStatus.OFFER)
        )


async def test_terminal_status_cannot_advance(session):
    pid = await _profile(session)
    cid = await _company(session)
    service = _service(session)
    app_obj = await service.track(pid, ApplicationCreate(company_id=cid))
    await service.advance(
        app_obj.id, ApplicationStatusUpdate(status=ApplicationStatus.REJECTED)
    )

    with pytest.raises(ValidationError):
        await service.advance(
            app_obj.id, ApplicationStatusUpdate(status=ApplicationStatus.APPLIED)
        )


async def test_advance_same_status_is_allowed_noop(session):
    pid = await _profile(session)
    cid = await _company(session)
    service = _service(session)
    app_obj = await service.track(pid, ApplicationCreate(company_id=cid))

    # Re-asserting current status records a note but stays valid.
    advanced = await service.advance(
        app_obj.id,
        ApplicationStatusUpdate(status=ApplicationStatus.SAVED, note="still keen"),
    )
    assert advanced.status is ApplicationStatus.SAVED
    assert len(advanced.events) == 2


async def test_add_note_keeps_status(session):
    pid = await _profile(session)
    cid = await _company(session)
    service = _service(session)
    app_obj = await service.track(pid, ApplicationCreate(company_id=cid))

    noted = await service.add_note(app_obj.id, ApplicationNote(note="Referred by Sam"))
    assert noted.status is ApplicationStatus.SAVED
    assert noted.notes == "Referred by Sam"
    assert noted.events[-1].from_status == noted.events[-1].to_status


async def test_list_filters_by_status_and_company(session):
    pid = await _profile(session)
    cid1 = await _company(session, "Stripe")
    cid2 = await _company(session, "Datadog")
    service = _service(session)
    a1 = await service.track(pid, ApplicationCreate(company_id=cid1))
    await service.advance(
        a1.id, ApplicationStatusUpdate(status=ApplicationStatus.APPLIED)
    )
    await service.track(pid, ApplicationCreate(company_id=cid2))

    applied = await service.list_for_profile(pid, status=ApplicationStatus.APPLIED)
    assert [a.id for a in applied] == [a1.id]

    at_cid2 = await service.list_for_profile(pid, company_id=cid2)
    assert len(at_cid2) == 1
    assert at_cid2[0].company_id == cid2


async def test_delete_removes_application(session):
    pid = await _profile(session)
    cid = await _company(session)
    service = _service(session)
    app_obj = await service.track(pid, ApplicationCreate(company_id=cid))

    await service.delete(app_obj.id)
    with pytest.raises(NotFoundError):
        await service.get(app_obj.id)


async def test_track_unknown_profile_raises(session):
    cid = await _company(session)
    service = _service(session)
    with pytest.raises(NotFoundError):
        await service.track(999999, ApplicationCreate(company_id=cid))


async def test_track_listing_mismatch_raises(session):
    pid = await _profile(session)
    cid1 = await _company(session, "Stripe")
    cid2 = await _company(session, "Datadog")
    jid = await _listing(session, cid2)  # belongs to a different company
    service = _service(session)

    with pytest.raises(NotFoundError):
        await service.track(
            pid, ApplicationCreate(company_id=cid1, job_listing_id=jid)
        )
