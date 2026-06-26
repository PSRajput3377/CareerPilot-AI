"""Unit tests for the heuristic resume parser and extractor (Module 2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from careerpilot.backend.core.exceptions import ValidationError
from careerpilot.backend.services.resume_parsing.base import get_parser
from careerpilot.backend.services.resume_parsing.extractor import extract_text
from careerpilot.backend.services.resume_parsing.heuristic import HeuristicResumeParser

SAMPLE = Path(__file__).parent / "sample_resume.txt"


@pytest.fixture
def parsed():
    return HeuristicResumeParser().parse(SAMPLE.read_text())


def test_extracts_contact_info(parsed):
    assert parsed.email == "jane.engineer@example.com"
    assert parsed.phone is not None
    assert parsed.github_url == "https://github.com/janeqeng"
    assert parsed.linkedin_url == "https://linkedin.com/in/janeqeng"
    assert parsed.name == "Jane Q. Engineer"


def test_detects_technologies(parsed):
    names = {s.name for s in parsed.skills}
    # Canonicalized forms.
    assert "Python" in names
    assert "Go" in names
    assert "PostgreSQL" in names
    assert "Kubernetes" in names
    assert "AWS" in names
    assert "FastAPI" in names


def test_parses_experience_and_internship_flag(parsed):
    assert len(parsed.experiences) >= 2
    titles = {e.title for e in parsed.experiences}
    assert any("Senior Software Engineer" in t for t in titles)
    # The intern role is flagged.
    assert any(e.is_internship for e in parsed.experiences)


def test_parses_education_projects_achievements(parsed):
    assert any("Massachusetts Institute" in e.institution for e in parsed.educations)
    assert any("CareerPilot" in p.name for p in parsed.projects)
    assert len(parsed.achievements) == 2
    assert parsed.parser == "heuristic"


def test_extract_text_from_txt():
    text = extract_text(SAMPLE)
    assert "EXPERIENCE" in text


def test_extract_text_missing_file_raises():
    with pytest.raises(ValidationError):
        extract_text("/no/such/file.pdf")


def test_extract_text_unsupported_format_raises(tmp_path):
    bad = tmp_path / "resume.docx"
    bad.write_text("nope")
    with pytest.raises(ValidationError):
        extract_text(bad)


def test_get_parser_defaults_to_heuristic():
    # No API key configured in tests → heuristic.
    assert get_parser().name == "heuristic"
    assert get_parser("openai").name == "heuristic"  # falls back without key
