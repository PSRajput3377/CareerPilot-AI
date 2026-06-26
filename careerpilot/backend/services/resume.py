"""Resume parsing service (Module 2).

Orchestrates: extract text → parse to structured data → optionally persist into
a :class:`UserProfile` (Module 1). Persistence merges parsed sections into the
profile without clobbering existing curated data (skills are unioned; projects,
achievements, experience, and education are appended only when empty or
explicitly merged).
"""

from __future__ import annotations

from pathlib import Path

from careerpilot.backend.core.logging import get_logger
from careerpilot.backend.models.user_profile import (
    Achievement,
    Education,
    Experience,
    Project,
    Skill,
)
from careerpilot.backend.schemas.resume import ParsedResume, ResumeParseResult
from careerpilot.backend.services.resume_parsing.base import ResumeParser, get_parser
from careerpilot.backend.services.resume_parsing.extractor import (
    extract_text,
    extract_text_from_bytes,
)
from careerpilot.backend.services.user_profile import UserProfileService

logger = get_logger("services.resume")


class ResumeService:
    """Parse resumes and merge results into user profiles."""

    def __init__(
        self,
        profile_service: UserProfileService,
        parser: ResumeParser | None = None,
    ) -> None:
        self._profiles = profile_service
        self._parser = parser or get_parser()

    # -- Parsing only (no persistence) ------------------------------------- #

    def parse_text(self, text: str) -> ParsedResume:
        """Parse raw resume text into structured data."""
        parsed = self._parser.parse(text)
        logger.info(
            "Parsed resume via '%s': %d skills, %d experiences, %d projects",
            parsed.parser,
            len(parsed.skills),
            len(parsed.experiences),
            len(parsed.projects),
        )
        return parsed

    def parse_file(self, path: str | Path) -> ParsedResume:
        """Extract text from a file and parse it."""
        return self.parse_text(extract_text(path))

    def parse_bytes(self, data: bytes, filename: str) -> ParsedResume:
        """Extract text from uploaded bytes and parse it."""
        return self.parse_text(extract_text_from_bytes(data, filename))

    # -- Parse + persist --------------------------------------------------- #

    async def parse_file_into_profile(
        self, path: str | Path, profile_id: int
    ) -> ResumeParseResult:
        """Parse a resume file and merge it into an existing profile."""
        parsed = self.parse_file(path)
        await self.apply_to_profile(parsed, profile_id, resume_path=str(path))
        return ResumeParseResult(parsed=parsed, profile_id=profile_id, applied=True)

    async def apply_to_profile(
        self, parsed: ParsedResume, profile_id: int, resume_path: str | None = None
    ) -> None:
        profile = await self._profiles.get(profile_id)

        if resume_path:
            profile.resume_path = resume_path
        # Fill contact links only when the profile is missing them.
        if parsed.github_url and not profile.github_url:
            profile.github_url = parsed.github_url
        if parsed.linkedin_url and not profile.linkedin_url:
            profile.linkedin_url = parsed.linkedin_url
        if parsed.portfolio_url and not profile.portfolio_url:
            profile.portfolio_url = parsed.portfolio_url

        _merge_skills(profile.skills, parsed)
        profile.experiences.extend(
            Experience(
                company=e.company,
                title=e.title,
                location=e.location,
                start_date=e.start_date,
                end_date=e.end_date,
                description=e.description,
                is_internship=getattr(e, "is_internship", False),
            )
            for e in parsed.experiences
        )
        profile.educations.extend(
            Education(
                institution=ed.institution,
                degree=ed.degree,
                field_of_study=ed.field_of_study,
                start_date=ed.start_date,
                end_date=ed.end_date,
                grade=ed.grade,
            )
            for ed in parsed.educations
        )
        profile.projects.extend(
            Project(
                name=p.name,
                description=p.description,
                tech_stack=", ".join(p.tech_stack) if p.tech_stack else None,
                url=p.url,
            )
            for p in parsed.projects
        )
        profile.achievements.extend(Achievement(description=a) for a in parsed.achievements)

        await self._profiles.save(profile)
        logger.info("Applied parsed resume to profile id=%s", profile_id)


def _merge_skills(existing: list[Skill], parsed: ParsedResume) -> None:
    """Union parsed skills into existing ones (case-insensitive, no dups)."""
    have = {s.name.lower() for s in existing}
    for skill in parsed.skills:
        key = skill.name.lower()
        if key not in have:
            have.add(key)
            existing.append(
                Skill(name=skill.name, proficiency=skill.proficiency, years=skill.years)
            )
