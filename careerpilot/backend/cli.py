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
from careerpilot.backend.repositories.company import CompanyRepository
from careerpilot.backend.repositories.user_profile import UserProfileRepository
from careerpilot.backend.schemas.company import CompanySearchQuery
from careerpilot.backend.schemas.user_profile import UserProfileCreate, UserProfileRead
from careerpilot.backend.services.company import CompanyService
from careerpilot.backend.services.resume import ResumeService
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
    "discover-people": "Module 5 — People Discovery",
    "verify-emails": "Module 7 — Email Verification",
    "generate-cover-letter": "Module 9 — Cover Letter Generator",
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
