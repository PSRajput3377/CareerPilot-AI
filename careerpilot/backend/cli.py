"""CareerPilot AI command-line interface (Module 21).

Built with Typer + Rich. Commands call the same service layer as the API. As
later modules land, their command groups are registered here (discover-company,
verify-emails, send-email, follow-up, …). The full surface is stubbed so the CLI
contract is stable from day one.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from careerpilot.backend.core.security import generate_key
from careerpilot.backend.database.session import init_models, session_scope
from careerpilot.backend.models.application import ApplicationStatus
from careerpilot.backend.models.cover_letter import CoverLetterTone
from careerpilot.backend.models.person import PersonRole
from careerpilot.backend.repositories.application import ApplicationRepository
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.cover_letter import CoverLetterRepository
from careerpilot.backend.repositories.email_template import EmailTemplateRepository
from careerpilot.backend.repositories.email_verification import (
    EmailVerificationRepository,
)
from careerpilot.backend.repositories.job_listing import JobListingRepository
from careerpilot.backend.repositories.job_match import JobMatchRepository
from careerpilot.backend.repositories.person import PersonRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.application import (
    ApplicationCreate,
    ApplicationNote,
    ApplicationStatusUpdate,
)
from careerpilot.backend.schemas.company import CompanySearchQuery
from careerpilot.backend.schemas.cover_letter import CoverLetterRequest
from careerpilot.backend.schemas.email_template import RenderContext
from careerpilot.backend.schemas.person import PeopleSearchQuery
from careerpilot.backend.schemas.personalization import PersonalizationRequest
from careerpilot.backend.schemas.subject import SubjectRequest
from careerpilot.backend.schemas.user_profile import UserProfileCreate, UserProfileRead
from careerpilot.backend.services.application import ApplicationService
from careerpilot.backend.services.career_page import CareerPageService, detection_summary
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.cover_letter import CoverLetterService
from careerpilot.backend.services.email_pattern import (
    EmailPatternGenerator,
    EmailPatternService,
)
from careerpilot.backend.services.email_verification import EmailVerificationService
from careerpilot.backend.services.job_matching import JobMatchingService
from careerpilot.backend.services.people import PeopleService
from careerpilot.backend.services.personalization import PersonalizationService
from careerpilot.backend.services.resume import ResumeService
from careerpilot.backend.services.subject import SubjectService
from careerpilot.backend.services.templating import EmailTemplateService
from careerpilot.backend.services.user_profile import UserProfileService

app = typer.Typer(
    name="careerpilot",
    help="CareerPilot AI — AI-powered job search & outreach automation.",
    no_args_is_help=True,
)
console = Console()

profile_app = typer.Typer(help="Manage user profiles (Module 1).")
app.add_typer(profile_app, name="profile")


def _run(coro):
    """Run an async coroutine from a sync Typer command."""
    return asyncio.run(coro)


# --------------------------------------------------------------------------- #
# System commands
# --------------------------------------------------------------------------- #


@app.command()
def init_db() -> None:
    """Create database tables (dev convenience; use Alembic in prod)."""

    async def _do() -> None:
        await init_models()

    _run(_do())
    console.print("[green]Database tables created.[/green]")


@app.command()
def generate_encryption_key() -> None:
    """Print a fresh Fernet key for CAREERPILOT_ENCRYPTION_KEY."""
    console.print(generate_key())


# --------------------------------------------------------------------------- #
# Profile commands (Module 1)
# --------------------------------------------------------------------------- #


@profile_app.command("create")
def profile_create(
    name: Annotated[str, typer.Option(help="Full name")],
    email: Annotated[str, typer.Option(help="Contact email")],
    role: Annotated[str | None, typer.Option(help="Preferred role")] = None,
    location: Annotated[str | None, typer.Option(help="Preferred location")] = None,
    skills: Annotated[str | None, typer.Option(help="Comma-separated skills")] = None,
) -> None:
    """Create a new user profile."""
    skill_list = [{"name": s.strip()} for s in (skills or "").split(",") if s.strip()]
    payload = UserProfileCreate(
        name=name,
        email=email,
        preferred_role=role,
        preferred_location=location,
        skills=skill_list,
    )

    async def _do() -> UserProfileRead:
        async with session_scope() as session:
            service = UserProfileService(UserProfileRepository(session))
            profile = await service.create(payload)
            return UserProfileRead.model_validate(profile)

    result = _run(_do())
    console.print(f"[green]Created profile[/green] id={result.id} ({result.email})")


@profile_app.command("list")
def profile_list(
    limit: Annotated[int, typer.Option(help="Max rows")] = 50,
) -> None:
    """List user profiles in a table."""

    async def _do() -> list[UserProfileRead]:
        async with session_scope() as session:
            service = UserProfileService(UserProfileRepository(session))
            profiles = await service.list(limit=limit)
            return [UserProfileRead.model_validate(p) for p in profiles]

    profiles = _run(_do())
    table = Table(title="User Profiles")
    table.add_column("ID", justify="right")
    table.add_column("Name")
    table.add_column("Email")
    table.add_column("Preferred Role")
    for p in profiles:
        table.add_row(str(p.id), p.name, p.email, p.preferred_role or "-")
    console.print(table)


@app.command("parse-resume")
def parse_resume(
    file: Annotated[str, typer.Argument(help="Path to resume (.pdf or .txt)")],
    profile_id: Annotated[
        int | None, typer.Option(help="If set, merge results into this profile")
    ] = None,
) -> None:
    """Parse a resume and print structured data (Module 2).

    With --profile-id, the parsed data is merged into that profile.
    """

    async def _do():
        async with session_scope() as session:
            profile_service = UserProfileService(UserProfileRepository(session))
            resume_service = ResumeService(profile_service)
            if profile_id is not None:
                result = await resume_service.parse_file_into_profile(file, profile_id)
                return result.parsed
            return resume_service.parse_file(file)

    parsed = _run(_do())
    console.print(f"[green]Parsed resume[/green] (parser={parsed.parser})")
    console.print_json(parsed.model_dump_json(indent=2))
    if profile_id is not None:
        console.print(f"[green]Merged into profile id={profile_id}[/green]")


@app.command("discover-company")
def discover_company(
    name: Annotated[str, typer.Argument(help="Company name or keyword")],
    industry: Annotated[str | None, typer.Option(help="Filter by industry")] = None,
    location: Annotated[str | None, typer.Option(help="Filter by location")] = None,
    remote: Annotated[bool, typer.Option(help="Prefer remote-friendly")] = False,
    limit: Annotated[int, typer.Option(help="Max results")] = 20,
) -> None:
    """Discover companies and persist them (Module 3)."""
    query = CompanySearchQuery(
        name=name,
        industry=industry,
        location=location,
        remote=remote or None,
        limit=limit,
    )

    async def _do():
        async with session_scope() as session:
            service = CompanyService(CompanyRepository(session))
            companies = await service.discover(query)
            # Detach the data we need before the session closes.
            return [
                (c.id, c.name, c.industry, c.career_page, c.hiring_platform, c.source)
                for c in companies
            ]

    rows = _run(_do())
    table = Table(title=f"Discovered companies for '{name}'")
    table.add_column("ID", justify="right")
    table.add_column("Name")
    table.add_column("Industry")
    table.add_column("Career Page")
    table.add_column("ATS")
    table.add_column("Source")
    for cid, cname, ind, career, ats, source in rows:
        table.add_row(str(cid), cname, ind or "-", career or "-", ats or "-", source or "-")
    console.print(table)


@app.command("detect-career-page")
def detect_career_page(
    company_id: Annotated[int, typer.Argument(help="Company id to inspect")],
) -> None:
    """Detect a company's ATS platform and extract job listings (Module 4)."""

    async def _do():
        async with session_scope() as session:
            service = CareerPageService(
                CompanyRepository(session), JobListingRepository(session)
            )
            result = await service.detect_for_company(company_id)
            return (
                detection_summary(result.detection),
                result.detection.career_page,
                result.listings_saved,
            )

    summary, career_page, saved = _run(_do())
    console.print(f"[green]Detected:[/green] {summary}")
    console.print(f"Career page: {career_page or '-'}")
    console.print(f"Listings saved: {saved}")


@app.command("discover-people")
def discover_people(
    company_id: Annotated[int, typer.Argument(help="Company id to find people at")],
    role: Annotated[
        str | None, typer.Option(help="Filter by role (recruiter, engineer, ...)")
    ] = None,
    title: Annotated[str | None, typer.Option(help="Filter by title keyword")] = None,
    limit: Annotated[int, typer.Option(help="Max results")] = 20,
) -> None:
    """Discover recruiters and employees at a company and persist them (Module 5)."""
    role_enum = PersonRole(role) if role else None
    query = PeopleSearchQuery(role=role_enum, title=title, limit=limit)

    async def _do():
        async with session_scope() as session:
            service = PeopleService(
                CompanyRepository(session), PersonRepository(session)
            )
            people, saved = await service.discover_for_company(company_id, query)
            # Detach the data we need before the session closes.
            rows = [
                (p.id, p.full_name, p.role.value, p.title, p.email, p.email_source.value)
                for p in people
            ]
            return rows, saved

    rows, saved = _run(_do())
    table = Table(title=f"People at company id={company_id}")
    table.add_column("ID", justify="right")
    table.add_column("Name")
    table.add_column("Role")
    table.add_column("Title")
    table.add_column("Email")
    table.add_column("Email Source")
    for pid, name, prole, ptitle, email, esource in rows:
        table.add_row(
            str(pid), name, prole, ptitle or "-", email or "-", esource
        )
    console.print(table)
    console.print(f"[green]People saved:[/green] {saved}")


@app.command("guess-email")
def guess_email(
    full_name: Annotated[str, typer.Argument(help="Person's full name")],
    domain: Annotated[str, typer.Argument(help="Company domain, e.g. stripe.com")],
) -> None:
    """Generate ranked email guesses for a name + domain (Module 6).

    Stateless preview — does not touch the database. Guesses are unverified.
    """
    result = EmailPatternGenerator().generate(full_name, domain)
    table = Table(title=f"Email guesses for {full_name} @ {domain}")
    table.add_column("#", justify="right")
    table.add_column("Email")
    table.add_column("Pattern")
    table.add_column("Confidence", justify="right")
    for i, c in enumerate(result.candidates, start=1):
        table.add_row(str(i), c.email, c.pattern, f"{c.confidence:.0%}")
    console.print(table)
    if not result.candidates:
        console.print("[yellow]No candidates — need a domain and a first name.[/yellow]")


@app.command("guess-company-emails")
def guess_company_emails(
    company_id: Annotated[int, typer.Argument(help="Company id to fill emails for")],
    overwrite: Annotated[
        bool, typer.Option(help="Replace existing guess emails")
    ] = False,
) -> None:
    """Fill missing pattern emails for every person at a company (Module 6)."""

    async def _do():
        async with session_scope() as session:
            service = EmailPatternService(
                CompanyRepository(session), PersonRepository(session)
            )
            results = await service.guess_for_company(company_id, overwrite=overwrite)
            return [(r.person_id, r.filled, r.email) for r in results]

    rows = _run(_do())
    table = Table(title=f"Pattern emails for company id={company_id}")
    table.add_column("Person ID", justify="right")
    table.add_column("Filled")
    table.add_column("Email")
    for pid, filled, email in rows:
        table.add_row(str(pid), "yes" if filled else "no", email or "-")
    console.print(table)
    console.print(f"[green]Filled:[/green] {sum(1 for _, f, _ in rows if f)}/{len(rows)}")


@app.command("check-email")
def check_email(
    email: Annotated[str, typer.Argument(help="Email address to verify")],
) -> None:
    """Verify a single email's deliverability (Module 7, stateless)."""

    async def _do():
        async with session_scope() as session:
            service = EmailVerificationService(
                CompanyRepository(session),
                PersonRepository(session),
                EmailVerificationRepository(session),
            )
            outcome = await service.check(email)
            return outcome

    outcome = _run(_do())
    color = {
        "valid": "green",
        "risky": "yellow",
        "invalid": "red",
        "unknown": "white",
    }.get(outcome.status.value, "white")
    console.print(
        f"[{color}]{outcome.status.value.upper()}[/{color}] "
        f"{outcome.email} (confidence {outcome.confidence:.0%})"
    )
    console.print(f"Reason: {outcome.reason or '-'}")


@app.command("verify-emails")
def verify_emails(
    company_id: Annotated[int, typer.Argument(help="Company id to verify people for")],
) -> None:
    """Verify deliverability for every person with an email at a company (Module 7)."""

    async def _do():
        async with session_scope() as session:
            service = EmailVerificationService(
                CompanyRepository(session),
                PersonRepository(session),
                EmailVerificationRepository(session),
            )
            results = await service.verify_company(company_id)
            return [
                (r.person_id, r.outcome.email, r.outcome.status.value, r.email_verified)
                for r in results
            ]

    rows = _run(_do())
    table = Table(title=f"Email verification for company id={company_id}")
    table.add_column("Person ID", justify="right")
    table.add_column("Email")
    table.add_column("Status")
    table.add_column("Verified")
    for pid, email, status, verified in rows:
        table.add_row(str(pid), email or "-", status, "yes" if verified else "no")
    console.print(table)
    valid = sum(1 for _, _, s, _ in rows if s == "valid")
    console.print(f"[green]Valid:[/green] {valid}/{len(rows)}")


@app.command("match-jobs")
def match_jobs(
    profile_id: Annotated[int, typer.Argument(help="Profile id to match")],
    company_id: Annotated[int, typer.Argument(help="Company id whose jobs to score")],
    limit: Annotated[int, typer.Option(help="Max rows to show")] = 20,
) -> None:
    """Score a profile against a company's job listings, ranked (Module 8)."""

    async def _do():
        async with session_scope() as session:
            service = JobMatchingService(
                UserProfileRepository(session),
                CompanyRepository(session),
                JobListingRepository(session),
                JobMatchRepository(session),
            )
            results = await service.match_company(profile_id, company_id)
            return [
                (
                    r.job_listing_id,
                    r.title,
                    r.match.score,
                    r.match.skill_score,
                    ", ".join(r.match.matched_skills) or "-",
                    ", ".join(r.match.missing_skills) or "-",
                )
                for r in results[:limit]
            ]

    rows = _run(_do())
    table = Table(title=f"Job matches: profile {profile_id} × company {company_id}")
    table.add_column("Job ID", justify="right")
    table.add_column("Title")
    table.add_column("Score", justify="right")
    table.add_column("Skills", justify="right")
    table.add_column("Matched")
    table.add_column("Missing")
    for jid, title, score, skill, matched, missing in rows:
        table.add_row(
            str(jid), title, f"{score:.0%}", f"{skill:.0%}", matched, missing
        )
    console.print(table)
    if not rows:
        console.print(
            "[yellow]No job listings for this company — run "
            "detect-career-page first.[/yellow]"
        )


@app.command("generate-cover-letter")
def generate_cover_letter(
    profile_id: Annotated[int, typer.Argument(help="Profile id")],
    company_id: Annotated[int, typer.Argument(help="Target company id")],
    job_listing_id: Annotated[
        int | None, typer.Option(help="Target a specific job listing")
    ] = None,
    tone: Annotated[
        str, typer.Option(help="professional | enthusiastic | concise")
    ] = "professional",
    save: Annotated[bool, typer.Option(help="Persist the draft")] = True,
) -> None:
    """Generate a personalized cover letter draft (Module 9).

    The letter is a draft for review — it is never sent automatically.
    """
    request = CoverLetterRequest(
        company_id=company_id,
        job_listing_id=job_listing_id,
        tone=CoverLetterTone(tone),
        save=save,
    )

    async def _do():
        async with session_scope() as session:
            service = CoverLetterService(
                UserProfileRepository(session),
                CompanyRepository(session),
                JobListingRepository(session),
                CoverLetterRepository(session),
                JobMatchRepository(session),
            )
            draft, saved = await service.generate(profile_id, request)
            return draft, (saved.id if saved else None)

    draft, saved_id = _run(_do())
    console.print(f"[bold]Subject:[/bold] {draft.subject}")
    console.print()
    console.print(draft.body)
    console.print()
    console.print(
        f"[dim]({draft.word_count} words, tone={draft.tone.value}, "
        f"generator={draft.generator})[/dim]"
    )
    if saved_id is not None:
        console.print(f"[green]Saved cover letter id={saved_id}[/green]")


@app.command("generate-subjects")
def generate_subjects(
    profile_id: Annotated[int, typer.Option(help="Candidate profile id")],
    company_id: Annotated[int | None, typer.Option(help="Target company id")] = None,
    person_id: Annotated[int | None, typer.Option(help="Recipient person id")] = None,
    job_listing_id: Annotated[
        int | None, typer.Option(help="Target job listing id")
    ] = None,
    limit: Annotated[int, typer.Option(help="Max subjects")] = 5,
) -> None:
    """Generate ranked email subject lines for an outreach context (Module 11)."""
    request = SubjectRequest(
        profile_id=profile_id,
        company_id=company_id,
        person_id=person_id,
        job_listing_id=job_listing_id,
        limit=limit,
    )

    async def _do():
        async with session_scope() as session:
            service = SubjectService(
                UserProfileRepository(session),
                CompanyRepository(session),
                PersonRepository(session),
                JobListingRepository(session),
            )
            result = await service.generate(request)
            return [
                (c.text, c.style.value, c.confidence, c.within_length)
                for c in result.candidates
            ]

    rows = _run(_do())
    table = Table(title="Subject line ideas")
    table.add_column("#", justify="right")
    table.add_column("Subject")
    table.add_column("Style")
    table.add_column("Score", justify="right")
    table.add_column("Len OK")
    for i, (text, style, conf, within) in enumerate(rows, start=1):
        table.add_row(str(i), text, style, f"{conf:.0%}", "yes" if within else "no")
    console.print(table)


def _template_service(session) -> EmailTemplateService:
    return EmailTemplateService(
        EmailTemplateRepository(session),
        UserProfileRepository(session),
        CompanyRepository(session),
        PersonRepository(session),
        JobListingRepository(session),
    )


@app.command("personalize")
def personalize(
    profile_id: Annotated[int, typer.Option(help="Candidate profile id")],
    person_id: Annotated[int, typer.Option(help="Recipient person id")],
    company_id: Annotated[int | None, typer.Option(help="Target company id")] = None,
    job_listing_id: Annotated[
        int | None, typer.Option(help="Target job listing id")
    ] = None,
    template_id: Annotated[
        int | None, typer.Option(help="Base template to enrich")
    ] = None,
    tone: Annotated[
        str, typer.Option(help="professional | enthusiastic | concise")
    ] = "professional",
) -> None:
    """Compose a personalized outreach draft (Module 12).

    Ties together the profile, recipient, role, skills, and an optional template
    into one tailored email. The draft is for review — it is never sent.
    """
    request = PersonalizationRequest(
        profile_id=profile_id,
        person_id=person_id,
        company_id=company_id,
        job_listing_id=job_listing_id,
        template_id=template_id,
        tone=CoverLetterTone(tone),
    )

    async def _do():
        async with session_scope() as session:
            service = PersonalizationService(
                UserProfileRepository(session),
                CompanyRepository(session),
                PersonRepository(session),
                JobListingRepository(session),
                JobMatchRepository(session),
                EmailTemplateRepository(session),
                SubjectService(
                    UserProfileRepository(session),
                    CompanyRepository(session),
                    PersonRepository(session),
                    JobListingRepository(session),
                ),
                _template_service(session),
            )
            return await service.personalize(request)

    draft = _run(_do())
    console.print(f"[bold]Subject:[/bold] {draft.subject}")
    console.print()
    console.print(draft.body)
    console.print()
    console.print(
        f"[dim]({draft.word_count} words, tone={draft.tone.value}, "
        f"personalization {draft.personalization_score:.0%}, engine={draft.engine})[/dim]"
    )
    if draft.personalization_signals:
        console.print(
            f"[dim]Signals: {', '.join(draft.personalization_signals)}[/dim]"
        )
    if draft.missing_placeholders:
        console.print(
            "[yellow]Missing placeholders (left intact): "
            f"{', '.join(draft.missing_placeholders)}[/yellow]"
        )


@app.command("list-templates")
def list_templates() -> None:
    """List available email templates, seeding built-ins if needed (Module 10)."""

    async def _do():
        async with session_scope() as session:
            service = _template_service(session)
            templates = await service.list()
            return [
                (t.id, t.name, t.category.value, "builtin" if t.is_builtin else "custom")
                for t in templates
            ]

    rows = _run(_do())
    table = Table(title="Email Templates")
    table.add_column("ID", justify="right")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Kind")
    for tid, name, category, kind in rows:
        table.add_row(str(tid), name, category, kind)
    console.print(table)


@app.command("render-template")
def render_template_cmd(
    template_id: Annotated[int, typer.Argument(help="Template id to render")],
    profile_id: Annotated[int, typer.Option(help="Candidate profile id")],
    company_id: Annotated[int | None, typer.Option(help="Target company id")] = None,
    person_id: Annotated[int | None, typer.Option(help="Recipient person id")] = None,
    job_listing_id: Annotated[
        int | None, typer.Option(help="Target job listing id")
    ] = None,
) -> None:
    """Render an email template against a resolved context (Module 10)."""
    ctx = RenderContext(
        profile_id=profile_id,
        company_id=company_id,
        person_id=person_id,
        job_listing_id=job_listing_id,
    )

    async def _do():
        async with session_scope() as session:
            service = _template_service(session)
            return await service.render(template_id, ctx)

    rendered = _run(_do())
    console.print(f"[bold]Subject:[/bold] {rendered.subject}")
    console.print()
    console.print(rendered.body)
    if rendered.missing_placeholders:
        console.print()
        console.print(
            "[yellow]Missing placeholders (left intact): "
            f"{', '.join(rendered.missing_placeholders)}[/yellow]"
        )


# --------------------------------------------------------------------------- #
# Application tracking commands (Module 13)
# --------------------------------------------------------------------------- #


def _application_service(session) -> ApplicationService:
    return ApplicationService(
        UserProfileRepository(session),
        CompanyRepository(session),
        JobListingRepository(session),
        ApplicationRepository(session),
    )


def _application_view(app_obj) -> dict:
    """Extract a printable snapshot while the session is still open."""
    return {
        "id": app_obj.id,
        "company_id": app_obj.company_id,
        "job_listing_id": app_obj.job_listing_id,
        "status": app_obj.status.value,
        "events": [
            (
                ev.to_status.value
                if ev.from_status is None or ev.from_status == ev.to_status
                else f"{ev.from_status.value} → {ev.to_status.value}",
                ev.note or "",
            )
            for ev in app_obj.events
        ],
    }


def _print_application(view: dict) -> None:
    """Render an application snapshot and its timeline as a table."""
    target = f"company {view['company_id']}"
    if view["job_listing_id"] is not None:
        target += f" / job {view['job_listing_id']}"
    console.print(
        f"[bold]Application id={view['id']}[/bold] "
        f"({target}) — status [cyan]{view['status']}[/cyan]"
    )
    table = Table(title="Timeline")
    table.add_column("#", justify="right")
    table.add_column("Change")
    table.add_column("Note")
    for i, (change, note) in enumerate(view["events"], start=1):
        table.add_row(str(i), change, note)
    console.print(table)


@app.command("track-application")
def track_application(
    profile_id: Annotated[int, typer.Argument(help="Profile id")],
    company_id: Annotated[int, typer.Argument(help="Target company id")],
    job_listing_id: Annotated[
        int | None, typer.Option(help="Target a specific job listing")
    ] = None,
    status: Annotated[
        str, typer.Option(help="Initial status (default: saved)")
    ] = "saved",
    notes: Annotated[str | None, typer.Option(help="Initial note")] = None,
) -> None:
    """Start tracking a job application (Module 13).

    Idempotent on the (profile, company, role) target — re-tracking returns the
    existing application.
    """
    request = ApplicationCreate(
        company_id=company_id,
        job_listing_id=job_listing_id,
        status=ApplicationStatus(status),
        notes=notes,
    )

    async def _do():
        async with session_scope() as session:
            service = _application_service(session)
            app_obj = await service.track(profile_id, request)
            return _application_view(app_obj)

    _print_application(_run(_do()))


@app.command("list-applications")
def list_applications(
    profile_id: Annotated[int, typer.Argument(help="Profile id")],
    status: Annotated[
        str | None, typer.Option(help="Filter by status")
    ] = None,
    company_id: Annotated[
        int | None, typer.Option(help="Filter by company id")
    ] = None,
    limit: Annotated[int, typer.Option(help="Max rows")] = 50,
) -> None:
    """List a profile's tracked applications (Module 13)."""

    async def _do():
        async with session_scope() as session:
            service = _application_service(session)
            apps = await service.list_for_profile(
                profile_id,
                status=ApplicationStatus(status) if status else None,
                company_id=company_id,
                limit=limit,
            )
            return [
                (a.id, a.company_id, a.job_listing_id, a.status.value, len(a.events))
                for a in apps
            ]

    rows = _run(_do())
    table = Table(title="Tracked applications")
    table.add_column("ID", justify="right")
    table.add_column("Company", justify="right")
    table.add_column("Job")
    table.add_column("Status")
    table.add_column("Events", justify="right")
    for aid, cid, jid, st, n_events in rows:
        table.add_row(str(aid), str(cid), str(jid) if jid else "-", st, str(n_events))
    console.print(table)


@app.command("update-application")
def update_application(
    application_id: Annotated[int, typer.Argument(help="Application id")],
    status: Annotated[str, typer.Argument(help="New status")],
    note: Annotated[str | None, typer.Option(help="Note for the timeline")] = None,
) -> None:
    """Advance a tracked application to a new status (Module 13)."""

    async def _do():
        async with session_scope() as session:
            service = _application_service(session)
            app_obj = await service.advance(
                application_id,
                ApplicationStatusUpdate(status=ApplicationStatus(status), note=note),
            )
            return _application_view(app_obj)

    _print_application(_run(_do()))


@app.command("note-application")
def note_application(
    application_id: Annotated[int, typer.Argument(help="Application id")],
    note: Annotated[str, typer.Argument(help="Note text")],
) -> None:
    """Append a note to an application's timeline without changing status (Module 13)."""

    async def _do():
        async with session_scope() as session:
            service = _application_service(session)
            app_obj = await service.add_note(application_id, ApplicationNote(note=note))
            return _application_view(app_obj)

    _print_application(_run(_do()))


@profile_app.command("show")
def profile_show(profile_id: int) -> None:
    """Show a single profile as JSON."""

    async def _do() -> UserProfileRead:
        async with session_scope() as session:
            service = UserProfileService(UserProfileRepository(session))
            profile = await service.get(profile_id)
            return UserProfileRead.model_validate(profile)

    result = _run(_do())
    console.print_json(result.model_dump_json())


# --------------------------------------------------------------------------- #
# Stubs for upcoming modules — keep the CLI surface stable (Modules 2-22).
# Each raises a clear "coming soon" message so the contract is discoverable.
# --------------------------------------------------------------------------- #

_UPCOMING = {
    "send-email": "Module 15 — Email Sending",
    "follow-up": "Module 17 — Follow-up Generator",
    "dashboard": "Module 16 — Analytics Dashboard",
}


def _make_stub(command_name: str, description: str):
    def _stub(
        args: Annotated[
            list[str] | None, typer.Argument(help="Arguments (ignored for now)")
        ] = None,
    ) -> None:
        console.print(f"[yellow]'{command_name}' is not implemented yet ({description}).[/yellow]")
        raise typer.Exit(code=1)

    _stub.__doc__ = f"[Planned] {description}."
    return _stub


for _name, _desc in _UPCOMING.items():
    app.command(name=_name)(_make_stub(_name, _desc))


if __name__ == "__main__":  # pragma: no cover
    app()
