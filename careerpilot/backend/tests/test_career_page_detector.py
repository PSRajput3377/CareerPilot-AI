"""Unit tests for the pattern career-page detector (Module 4)."""

from __future__ import annotations

import pytest

from careerpilot.backend.models.job_listing import ATSPlatform
from careerpilot.backend.schemas.job_listing import JobListingCreate
from careerpilot.backend.services.career_page.base import CompanyLike, get_detector
from careerpilot.backend.services.career_page.pattern import PatternCareerPageDetector


@pytest.mark.parametrize(
    "career_page,expected",
    [
        ("https://boards.greenhouse.io/acme", ATSPlatform.GREENHOUSE),
        ("https://jobs.lever.co/acme", ATSPlatform.LEVER),
        ("https://jobs.ashbyhq.com/acme", ATSPlatform.ASHBY),
        ("https://acme.myworkdayjobs.com/careers", ATSPlatform.WORKDAY),
        ("https://careers.smartrecruiters.com/acme", ATSPlatform.SMARTRECRUITERS),
        ("https://acme.bamboohr.com/jobs", ATSPlatform.BAMBOOHR),
        ("https://jobs.jobvite.com/acme", ATSPlatform.JOBVITE),
        ("https://acme.taleo.net", ATSPlatform.ORACLE),
        ("https://acme.successfactors.com", ATSPlatform.SAP_SUCCESSFACTORS),
    ],
)
async def test_detects_each_ats_from_url(career_page, expected):
    detector = PatternCareerPageDetector()
    detection = await detector.detect(CompanyLike(name="Acme", career_page=career_page))
    assert detection.platform == expected
    assert detection.confidence >= 0.8


async def test_slug_takes_priority_with_high_confidence():
    detector = PatternCareerPageDetector()
    detection = await detector.detect(
        CompanyLike(name="Acme", hiring_platform="ashby", career_page="https://acme.com/jobs")
    )
    assert detection.platform == ATSPlatform.ASHBY
    assert detection.confidence == pytest.approx(0.95)


async def test_custom_when_career_page_but_no_known_ats():
    detector = PatternCareerPageDetector()
    detection = await detector.detect(
        CompanyLike(name="Acme", career_page="https://acme.com/careers")
    )
    assert detection.platform == ATSPlatform.CUSTOM


async def test_unknown_when_no_signals():
    detector = PatternCareerPageDetector()
    detection = await detector.detect(CompanyLike(name="Acme"))
    assert detection.platform == ATSPlatform.UNKNOWN
    assert detection.confidence == 0.0


async def test_listings_fixture_returned():
    fixture = {
        "Acme": [
            JobListingCreate(external_id="1", title="Backend Engineer", remote=True),
            JobListingCreate(external_id="2", title="Frontend Engineer"),
        ]
    }
    detector = PatternCareerPageDetector(listings_fixture=fixture)
    detection = await detector.detect(
        CompanyLike(name="Acme", hiring_platform="greenhouse")
    )
    assert len(detection.listings) == 2


def test_get_detector_defaults_to_pattern():
    assert get_detector().name == "pattern"
    assert get_detector("http").name == "pattern"  # not built yet → fallback
