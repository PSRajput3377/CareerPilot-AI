"""Deterministic, offline resume parser (Module 2).

Uses section detection + regexes + a curated technology lexicon. No network or
LLM dependency, so it is fast, free, and fully testable. An LLM-backed parser
can later supersede it via the registry while keeping this as the fallback.
"""

from __future__ import annotations

import re

from careerpilot.backend.schemas.resume import ParsedProject, ParsedResume
from careerpilot.backend.schemas.user_profile import (
    EducationCreate,
    ExperienceCreate,
    SkillCreate,
)
from careerpilot.backend.services.resume_parsing.base import ResumeParser

# --------------------------------------------------------------------------- #
# Patterns & lexicons
# --------------------------------------------------------------------------- #

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}")
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+", re.I)
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+", re.I)
URL_RE = re.compile(r"https?://[^\s)>\]]+", re.I)
INTERNSHIP_RE = re.compile(r"\bintern(ship)?\b", re.I)

# Section header keywords → canonical section name.
SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "skills": ("skills", "technical skills", "technologies", "tech stack", "core competencies"),
    "experience": (
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "work history",
    ),
    "education": ("education", "academic background", "academics"),
    "projects": ("projects", "personal projects", "selected projects"),
    "achievements": ("achievements", "awards", "honors", "accomplishments", "certifications"),
}

# Curated, lowercase technology lexicon for skill/tech-stack detection.
TECH_LEXICON: frozenset[str] = frozenset(
    {
        "python", "java", "javascript", "typescript", "go", "golang", "rust", "c", "c++",
        "c#", "ruby", "php", "kotlin", "swift", "scala", "r", "matlab", "perl", "dart",
        "html", "css", "sql", "nosql", "bash", "shell",
        "react", "next.js", "nextjs", "vue", "angular", "svelte", "node", "node.js",
        "express", "django", "flask", "fastapi", "spring", "spring boot", "rails",
        "laravel", ".net", "asp.net", "tailwind", "bootstrap",
        "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis", "cassandra",
        "dynamodb", "elasticsearch", "kafka", "rabbitmq", "snowflake", "bigquery",
        "aws", "gcp", "azure", "docker", "kubernetes", "k8s", "terraform", "ansible",
        "jenkins", "github actions", "gitlab ci", "circleci", "helm", "prometheus",
        "grafana", "datadog", "nginx", "linux",
        "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn", "pandas", "numpy",
        "spark", "hadoop", "airflow", "langchain", "openai", "huggingface",
        "git", "graphql", "rest", "grpc", "celery", "websocket",
    }
)


class HeuristicResumeParser(ResumeParser):
    """Rule-based parser. Deterministic and dependency-free."""

    name = "heuristic"

    def parse(self, text: str) -> ParsedResume:
        normalized = _normalize(text)
        sections = _split_sections(normalized)

        skills_block = sections.get("skills", "")
        tech_stack = _detect_technologies(skills_block or normalized)
        skills = [SkillCreate(name=t) for t in tech_stack]

        return ParsedResume(
            name=_guess_name(normalized),
            email=_first(EMAIL_RE, normalized),
            phone=_first(PHONE_RE, normalized),
            github_url=_normalize_url(_first(GITHUB_RE, normalized)),
            linkedin_url=_normalize_url(_first(LINKEDIN_RE, normalized)),
            skills=skills,
            tech_stack=tech_stack,
            experiences=_parse_experiences(sections.get("experience", "")),
            educations=_parse_education(sections.get("education", "")),
            projects=_parse_projects(sections.get("projects", "")),
            achievements=_parse_bullets(sections.get("achievements", "")),
            parser=self.name,
        )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of blank lines but preserve single newlines (section structure).
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _first(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0) if match else None


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    return url if url.startswith("http") else f"https://{url}"


def _guess_name(text: str) -> str | None:
    """Heuristic: the first non-empty line that looks like a person's name."""
    for line in text.splitlines():
        line = line.strip()
        if not line or EMAIL_RE.search(line) or URL_RE.search(line):
            continue
        words = line.split()
        if 1 < len(words) <= 4 and all(w[:1].isalpha() for w in words):
            # Avoid all-caps section headers.
            if not _is_section_header(line):
                return line
        break
    return None


def _is_section_header(line: str) -> bool:
    candidate = line.strip().lower().rstrip(":")
    return any(candidate == alias for aliases in SECTION_ALIASES.values() for alias in aliases)


def _canonical_section(line: str) -> str | None:
    candidate = line.strip().lower().rstrip(":")
    if len(candidate) > 40:
        return None
    for canonical, aliases in SECTION_ALIASES.items():
        if candidate in aliases:
            return canonical
    return None


def _split_sections(text: str) -> dict[str, str]:
    """Partition resume text into canonical sections by header lines."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        canonical = _canonical_section(line)
        if canonical is not None:
            current = canonical
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def _detect_technologies(text: str) -> list[str]:
    """Find known technologies, preserving first-seen order, deduped."""
    lowered = text.lower()
    found: list[str] = []
    seen: set[str] = set()
    # Longer terms first so "spring boot" wins over "spring".
    for tech in sorted(TECH_LEXICON, key=len, reverse=True):
        pattern = r"(?<![A-Za-z0-9+#.])" + re.escape(tech) + r"(?![A-Za-z0-9+#])"
        if re.search(pattern, lowered) and tech not in seen:
            seen.add(tech)
            found.append(_canonical_tech(tech))
    # Stable, human-friendly ordering by first appearance in the text.
    found.sort(key=lambda t: lowered.find(t.lower()))
    return found


def _canonical_tech(tech: str) -> str:
    overrides = {
        "golang": "Go",
        "node": "Node.js",
        "nodejs": "Node.js",
        "next.js": "Next.js",
        "nextjs": "Next.js",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "mysql": "MySQL",
        "mongodb": "MongoDB",
        "dynamodb": "DynamoDB",
        "nosql": "NoSQL",
        "k8s": "Kubernetes",
        "sklearn": "scikit-learn",
        "scikit-learn": "scikit-learn",
        "aws": "AWS",
        "gcp": "GCP",
        "sql": "SQL",
        "html": "HTML",
        "css": "CSS",
        "php": "PHP",
        "rest": "REST",
        "grpc": "gRPC",
        "graphql": "GraphQL",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "fastapi": "FastAPI",
        "github actions": "GitHub Actions",
        "gitlab ci": "GitLab CI",
        "circleci": "CircleCI",
        "pytorch": "PyTorch",
        "tensorflow": "TensorFlow",
        "openai": "OpenAI",
        "huggingface": "HuggingFace",
        "langchain": "LangChain",
        "rabbitmq": "RabbitMQ",
        "bigquery": "BigQuery",
        "websocket": "WebSocket",
        "asp.net": "ASP.NET",
        ".net": ".NET",
        "matlab": "MATLAB",
    }
    if tech in overrides:
        return overrides[tech]
    # Title-case multiword, keep short acronyms/symbols verbatim otherwise.
    if " " in tech:
        return tech.title()
    return tech if any(c in tech for c in ".+#") else tech.capitalize()


def _parse_bullets(block: str) -> list[str]:
    """Split a block into bullet/line items."""
    items: list[str] = []
    for raw in block.splitlines():
        line = raw.strip().lstrip("•-*▪◦·").strip()
        if line:
            items.append(line)
    return items


def _parse_experiences(block: str) -> list[ExperienceCreate]:
    """Best-effort: each non-bullet header line is a role.

    Lines like "Software Engineer, Acme Corp" or "Acme Corp — Software Engineer".
    Bullet lines are treated as the description of the preceding role.
    """
    experiences: list[ExperienceCreate] = []
    current_desc: list[str] = []

    def flush(title: str, company: str) -> None:
        experiences.append(
            ExperienceCreate(
                company=company or "Unknown",
                title=title or "Unknown",
                description="\n".join(current_desc).strip() or None,
                is_internship=bool(INTERNSHIP_RE.search(f"{title} {company}")),
            )
        )

    pending: tuple[str, str] | None = None
    for raw in block.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line[:1] in "•-*▪◦·":
            current_desc.append(line.lstrip("•-*▪◦·").strip())
            continue
        # New header: flush previous.
        if pending is not None:
            flush(*pending)
            current_desc = []
        title, company = _split_title_company(line)
        pending = (title, company)
    if pending is not None:
        flush(*pending)
    return experiences


def _split_title_company(line: str) -> tuple[str, str]:
    for sep in ("—", "–", " - ", " at ", ", ", " | ", "|"):
        if sep in line:
            left, right = line.split(sep, 1)
            return left.strip(), right.strip()
    return line.strip(), ""


def _parse_education(block: str) -> list[EducationCreate]:
    educations: list[EducationCreate] = []
    for raw in block.splitlines():
        line = raw.strip().lstrip("•-*▪◦·").strip()
        if not line:
            continue
        institution, degree = _split_title_company(line)
        educations.append(
            EducationCreate(
                institution=institution or line,
                degree=degree or None,
            )
        )
    return educations


def _parse_projects(block: str) -> list[ParsedProject]:
    projects: list[ParsedProject] = []
    current: ParsedProject | None = None
    for raw in block.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line[:1] in "•-*▪◦·":
            if current is not None and current.description is None:
                current.description = line.lstrip("•-*▪◦·").strip()
            continue
        if current is not None:
            projects.append(current)
        name, _ = _split_title_company(line)
        url = _first(URL_RE, line)
        current = ParsedProject(
            name=name or line,
            url=url,
            tech_stack=_detect_technologies(line),
        )
    if current is not None:
        projects.append(current)
    return projects
