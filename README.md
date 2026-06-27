# CareerPilot AI

> AI-powered Job Search, Referral, Outreach and Follow-up Automation Platform.

CareerPilot AI helps software engineers run their entire job search: discover
companies, find recruiters and employees, generate **personalized, human-sounding**
outreach, send it through authorized email accounts, and track applications and
follow-ups — automating the repetitive parts while keeping every message
respectful and individual.

> **Responsible use.** CareerPilot is built around a human-in-the-loop gate:
> outreach is drafted, reviewed, and only then sent. It uses publicly available
> information, prefers verified business emails over generated guesses, respects
> provider rate limits, and never auto-sends to unverified addresses.

---

## The outreach pipeline

```
Resume → Company Discovery → People Discovery
                                   ↓
                         Public email found?
                          ├── yes → verify deliverability
                          └── no  → generate common patterns → verify
                                   ↓
                      Generate personalized email
                                   ↓
                       Review before sending   ← human gate
                                   ↓
                  Send via Gmail / Outlook / SES / SMTP
                                   ↓
                 Track replies & schedule follow-ups
```

This contract drives the architecture: discovery → verification → drafting →
**review** → send → track. Sending is always a separate, explicit step.

---

## Status

Built incrementally, one module at a time, each production-quality and tested.

| Module | Area | Status |
| ------ | ---- | ------ |
| Foundation | Clean architecture, config, security, DB, logging, CLI/API spine | ✅ Done |
| 1 | User Profile | ✅ Done |
| 19 | Configuration (`config.yaml` + env) | ✅ Done |
| 20 | Security (secret encryption) | ✅ Done |
| 2 | Resume Parser | ✅ Done |
| 3 | Company Discovery | ✅ Done |
| 4 | Career Page Detection | ✅ Done |
| 5 | People Discovery | ✅ Done |
| 6 | Email Pattern Generator | ✅ Done |
| 7 | Email Verification | ✅ Done |
| 8 | Job Matching AI | ✅ Done |
| 9 | Cover Letter Generator | ✅ Done |
| 10 | Email Template Engine | ⏳ Planned |
| 11 | Subject Generator | ⏳ Planned |
| 12 | AI Personalization Engine | ⏳ Planned |
| 13 | Application Tracker | ⏳ Planned |
| 14 | Outreach Scheduler | ⏳ Planned |
| 15 | Email Sending | ⏳ Planned |
| 16 | Analytics Dashboard | ⏳ Planned |
| 17 | Follow-up Generator | ⏳ Planned |
| 18 | Logging (CSV artifacts) | ⏳ Planned |
| 21 | CLI | 🟦 Spine + profile commands |
| 22 | Web Dashboard | ⏳ Planned |
| 23 | Future integrations | 🧩 Designed for |

---

## How to Use — Step by Step

This guide walks you through setting up CareerPilot AI from scratch and using
every feature that is available today: **user profiles**, **resume parsing**, and
**company discovery**. Follow the steps in order the first time; later you can
jump straight to the command you need.

### What you need before starting

| Requirement | Details |
| ----------- | ------- |
| **Python** | 3.12 or newer (tested on 3.14) |
| **Git** | To clone the repository |
| **Terminal** | macOS Terminal, Linux shell, or Windows WSL |
| **Optional** | Docker Desktop — only if you want the PostgreSQL stack |

You do **not** need an OpenAI key, SMTP credentials, or any paid API to try the
current modules. Company discovery uses a built-in offline dataset; resume parsing
uses a heuristic parser (no LLM required).

---

### Step 1 — Clone the repository

```bash
git clone https://github.com/PSRajput3377/CareerPilot-AI.git
cd CareerPilot-AI
```

> **macOS tip:** Make sure you open the folder named `CareerPilot-AI` (or
> `automate email` if that is your local copy name) — **not** a similarly named
> folder with a trailing space. If Cursor/VS Code shows an almost-empty folder
> with only `.claude/`, you opened the wrong directory.

---

### Step 2 — Create a Python virtual environment

A virtual environment keeps CareerPilot's dependencies isolated from the rest of
your system.

```bash
python3 -m venv .venv
```

Activate it:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (Command Prompt)
.venv\Scripts\activate.bat

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

Your prompt should now show `(.venv)`. Every command below assumes this
environment is active.

---

### Step 3 — Install CareerPilot

```bash
pip install -e ".[dev]"
```

This installs the `careerpilot` CLI, the FastAPI server, and dev tools (pytest,
ruff, mypy). Verify the install:

```bash
careerpilot --help
```

You should see commands like `init-db`, `profile`, `parse-resume`, and
`discover-company`.

---

### Step 4 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` in any text editor. For local development the defaults work out of
the box, but you should set an encryption key so secrets can be stored properly:

```bash
careerpilot generate-encryption-key
```

Copy the printed key into `.env`:

```env
CAREERPILOT_ENCRYPTION_KEY=paste-the-key-here
```

**Key settings in `.env`:**

| Variable | Default | What it does |
| -------- | ------- | ------------ |
| `CAREERPILOT_ENV` | `development` | Runtime mode |
| `CAREERPILOT_DATABASE_URL` | SQLite file | Where data is stored |
| `CAREERPILOT_ENCRYPTION_KEY` | *(empty)* | Encrypts stored secrets |
| `CAREERPILOT_OPENAI_API_KEY` | *(empty)* | Only needed for future LLM features |

Non-secret behaviour (rate limits, scheduling windows, log paths) lives in
`config.yaml` and can be edited without touching `.env`.

---

### Step 5 — Initialize the database

```bash
careerpilot init-db
```

Expected output:

```
Database tables created.
```

This creates a local SQLite file (`careerpilot.db` by default) with tables for
profiles, companies, skills, experience, and education. In production you would
use PostgreSQL and Alembic migrations instead — see
[Deployment](docs/DEPLOYMENT.md).

---

### Step 6 — Create your job-search profile

A **profile** is your CareerPilot identity: name, email, target role, skills,
and (later) parsed resume data.

**CLI:**

```bash
careerpilot profile create \
  --name "Jane Engineer" \
  --email "jane@example.com" \
  --role "Backend Engineer" \
  --location "San Francisco, CA" \
  --skills "Python,Go,PostgreSQL,FastAPI"
```

Expected output:

```
Created profile id=1 (jane@example.com)
```

**List all profiles:**

```bash
careerpilot profile list
```

**View one profile as JSON:**

```bash
careerpilot profile show 1
```

Save the `id` — you will need it when parsing a resume into the profile.

---

### Step 7 — Parse your resume

CareerPilot extracts structured data (skills, experience, education, links) from
a `.pdf` or `.txt` resume.

**Option A — Parse only (preview, no save):**

```bash
careerpilot parse-resume careerpilot/backend/tests/sample_resume.txt
```

This prints JSON with the extracted fields. Use your own resume file path instead
of the sample.

**Option B — Parse and merge into your profile:**

```bash
careerpilot parse-resume /path/to/your/resume.pdf --profile-id 1
```

This parses the file **and** merges skills, experience, education, and links
into profile `1`. Run `careerpilot profile show 1` afterward to see the updated
profile.

**Via the API** (start the server first — see Step 9):

- `POST /api/v1/resumes/parse` — upload a file, get JSON back
- `POST /api/v1/resumes/parse-into-profile?profile_id=1` — upload and merge

---

### Step 8 — Discover companies

Search for companies to target in your job search. Results are saved to the
database so you can search them later.

```bash
careerpilot discover-company "Stripe"
```

Filter further:

```bash
careerpilot discover-company "Datadog" --industry "Observability" --remote --limit 10
```

The command prints a table with company ID, name, industry, career page URL, ATS
platform (Greenhouse, Ashby, etc.), and data source.

**Curated companies in the offline dataset:** Stripe, Datadog, Vercel, Notion,
Anthropic. Searching for a name not in the list still returns a synthesized
record (marked `stub:synthesized`) so you can test the full flow without
external APIs.

**Search companies already saved:**

Use the API after starting the server:

```bash
curl "http://localhost:8000/api/v1/companies/search?name=Stripe"
```

---

### Step 8b — Detect a company's career page (ATS)

Once a company is saved, detect which Applicant Tracking System it uses
(Greenhouse, Lever, Ashby, Workday, SmartRecruiters, BambooHR, Jobvite, Oracle,
SAP SuccessFactors, or a custom page) and extract any public job listings.

```bash
careerpilot detect-career-page 1     # 1 = the company id from Step 8
```

Expected output:

```
Detected: greenhouse (confidence 95%, detector pattern)
Career page: https://stripe.com/jobs
Listings saved: 0
```

Detection is offline and deterministic — it recognizes the ATS from the career
page URL and the discovered hiring-platform slug. The detected platform is saved
on the company (`ats_platform`).

**Via the API:**

- `POST /api/v1/companies/{id}/detect-career-page` — detect + persist
- `GET /api/v1/companies/{id}/jobs` — list extracted job listings

---

### Step 8c — Discover people at a company

Once a company is saved, find recruiters and employees to reach out to. People
are saved to the company so downstream modules (email verification, drafting,
sending) can target them.

```bash
careerpilot discover-people 1            # 1 = the company id from Step 8
```

Filter by role or title:

```bash
careerpilot discover-people 1 --role recruiter
careerpilot discover-people 1 --title "engineering manager" --limit 5
```

The command prints a table with person ID, name, role (recruiter, hiring
manager, engineer, …), title, email, and email source. Discovery is offline and
deterministic: well-known companies (Stripe, Anthropic) have a curated roster;
any other company gets a synthesized roster so you can exercise the full flow.

> **Email policy.** When a company domain is known, a likely `first.last@domain`
> address is attached and marked `public` — but **left unverified**. Verification
> is a separate step (Module 7), and nothing is ever auto-sent to an unverified
> address. People without a known domain are returned with no email.

**Via the API:**

- `POST /api/v1/companies/{id}/people/discover` — discover + persist
- `GET /api/v1/companies/{id}/people` — list saved people (filter by `role`, `title`, `department`)
- `GET /api/v1/people/{person_id}` — read one person
- `PATCH /api/v1/people/{person_id}` — update (e.g. mark `email_verified`)
- `DELETE /api/v1/people/{person_id}` — remove a person

---

### Step 8d — Guess business emails (when none was found)

When a person was discovered without a public email, CareerPilot can guess one
from the company domain using common corporate conventions
(`first.last@`, `flast@`, …). This is the *"no public email → generate common
patterns"* branch of the pipeline.

**Preview guesses for any name + domain (stateless, nothing saved):**

```bash
careerpilot guess-email "Jane Doe" stripe.com
```

This prints ranked candidates with the pattern that produced each and a
confidence score (rank-based, most-common pattern first):

```
1  jane.doe@stripe.com   {first}.{last}   100%
2  jdoe@stripe.com       {f}{last}         88%
3  jane@stripe.com       {first}           75%
...
```

**Fill missing emails for everyone discovered at a company:**

```bash
careerpilot guess-company-emails 1            # 1 = company id
careerpilot guess-company-emails 1 --overwrite  # also re-roll existing guesses
```

The best candidate is written onto each person who lacks an email, marked
`email_source = pattern` and **left unverified**.

> **Why unverified?** Guessed addresses are not confirmed deliverable. Per the
> outreach contract, a known **public** email is never overwritten by a guess,
> and nothing is auto-sent to an unverified address. Email verification is the
> next module (Module 7). Pattern templates are configurable under
> `email_patterns` in `config.yaml`.

**Via the API:**

- `GET /api/v1/email-patterns/preview?full_name=...&domain=...` — stateless preview
- `POST /api/v1/people/{person_id}/guess-email` — fill one person (`?overwrite=true` to replace a guess)
- `POST /api/v1/companies/{id}/people/guess-emails` — fill everyone at a company

---

### Step 8e — Verify email deliverability

Before any outreach, CareerPilot checks whether an email is likely deliverable.
This is the *"verify deliverability"* gate of the pipeline: a person's
`email_verified` flag is only set once their address passes, and nothing is sent
to an address that has not.

**Check any address (stateless, nothing saved):**

```bash
careerpilot check-email jane.doe@stripe.com
```

```
VALID jane.doe@stripe.com (confidence 75%)
Reason: Valid syntax and mail-accepting domain.
```

Verdicts are one of `valid`, `risky` (disposable domain or role mailbox like
`careers@`), `invalid` (malformed or non-mail domain), or `unknown`.

**Verify everyone discovered at a company:**

```bash
careerpilot verify-emails 1            # 1 = company id
```

Each person with an email is checked; the verdict is persisted, and
`email_verified` is set to `yes` only on a `valid` result.

> **Offline & deterministic.** Verification runs syntax, domain-plausibility,
> disposable-domain, and role-account checks with no network, so it is hermetic
> and testable. A live SMTP/DNS verifier can register later without changing any
> caller. Only a `valid` verdict flips `email_verified`; downstream sending
> (Module 15) refuses unverified addresses.

**Via the API:**

- `GET /api/v1/email-verification/check?email=...` — stateless check
- `POST /api/v1/people/{person_id}/verify-email` — verify + persist for one person
- `GET /api/v1/people/{person_id}/verifications` — list a person's verdicts
- `POST /api/v1/companies/{id}/people/verify-emails` — verify everyone at a company

---

### Step 8f — Match your profile to a company's jobs

Once a company's job listings have been extracted (Step 8b,
`detect-career-page`), score how well your profile fits each role. Matching
prioritizes which jobs to pursue and feeds personalization downstream.

```bash
careerpilot match-jobs 1 1     # profile_id  company_id
```

```
Job ID  Title                    Score  Skills  Matched                      Missing
1       Senior Backend Engineer  100%   100%    aws, fastapi, postgresql...  -
2       Frontend Designer        38%    50%     -                            -
```

Each match blends three components: **skills** (overlap between your skills and
those named in the job, the dominant factor), **title** (alignment with your
preferred role), and **location** (remote always fits; otherwise a location
match). The stored match also records matched/missing skills and a rationale.

> **Offline & deterministic.** Matching uses a heuristic scorer with no network,
> so it is hermetic and testable. An LLM-backed matcher can register later
> without changing callers — it falls back to the heuristic when no API key is
> configured (same pattern as the resume parser).

**Via the API:**

- `POST /api/v1/profiles/{id}/match/companies/{company_id}` — score all jobs at a company (ranked)
- `POST /api/v1/profiles/{id}/match/jobs/{job_listing_id}` — score one job
- `GET /api/v1/profiles/{id}/matches` — list stored matches (optionally `?company_id=`)

---

### Step 8g — Generate a cover letter

Draft a personalized, human-sounding cover letter for a profile targeting a
company (and optionally a specific role). The letter is a **draft for review** —
it is never sent automatically.

```bash
careerpilot generate-cover-letter 1 1                       # profile_id  company_id
careerpilot generate-cover-letter 1 1 --tone enthusiastic   # professional | enthusiastic | concise
careerpilot generate-cover-letter 1 1 --job-listing-id 3    # target a specific role
careerpilot generate-cover-letter 1 1 --no-save             # preview only, don't persist
```

The draft is grounded in concrete details — the specific role, the company and
its industry, and the candidate's overlapping skills (pulled from a job match
when one exists) — so it reads as individual rather than templated.

> **Offline & deterministic.** Generation uses a tone-aware template with no
> network, so it is hermetic and testable. An LLM-backed generator can register
> later without changing callers — it falls back to the template when no API key
> is configured (same pattern as the resume parser). Saved letters are drafts;
> sending is a separate, explicit step (Module 15).

**Via the API:**

- `POST /api/v1/profiles/{id}/cover-letters` — generate (persists unless `"save": false`)
- `GET /api/v1/profiles/{id}/cover-letters` — list a profile's drafts
- `GET /api/v1/cover-letters/{letter_id}` — read one draft
- `DELETE /api/v1/cover-letters/{letter_id}` — delete a draft

---

### Step 9 — Run the REST API (optional)

The API exposes the same features as the CLI, plus an interactive Swagger UI.

```bash
uvicorn careerpilot.backend.main:app --reload
```

Open **http://localhost:8000/docs** in your browser.

**Common endpoints:**

| Method | Endpoint | Purpose |
| ------ | -------- | ------- |
| `POST` | `/api/v1/profiles` | Create a profile |
| `GET` | `/api/v1/profiles` | List profiles |
| `GET` | `/api/v1/profiles/{id}` | Get one profile |
| `POST` | `/api/v1/resumes/parse` | Upload resume → JSON |
| `POST` | `/api/v1/resumes/parse-into-profile` | Upload + merge into profile |
| `POST` | `/api/v1/companies/discover` | Discover and save companies |
| `GET` | `/api/v1/companies/search` | Search saved companies |
| `POST` | `/api/v1/companies/{id}/people/discover` | Discover people at a company |
| `GET` | `/api/v1/companies/{id}/people` | List saved people for a company |
| `GET` | `/api/v1/email-patterns/preview` | Preview guessed emails (name + domain) |
| `POST` | `/api/v1/companies/{id}/people/guess-emails` | Fill missing emails for a company |
| `GET` | `/api/v1/email-verification/check` | Check an email's deliverability |
| `POST` | `/api/v1/companies/{id}/people/verify-emails` | Verify everyone at a company |
| `POST` | `/api/v1/profiles/{id}/match/companies/{company_id}` | Score a profile against a company's jobs |
| `GET` | `/api/v1/profiles/{id}/matches` | List a profile's ranked job matches |
| `POST` | `/api/v1/profiles/{id}/cover-letters` | Generate a cover letter draft |
| `GET` | `/api/v1/profiles/{id}/cover-letters` | List a profile's cover letter drafts |

**Example — create a profile via curl:**

```bash
curl -X POST http://localhost:8000/api/v1/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Engineer",
    "email": "jane@example.com",
    "preferred_role": "Backend Engineer",
    "skills": [{"name": "Python"}, {"name": "Go"}]
  }'
```

**Example — discover companies via curl:**

```bash
curl -X POST http://localhost:8000/api/v1/companies/discover \
  -H "Content-Type: application/json" \
  -d '{"name": "Vercel", "limit": 5}'
```

---

### Step 10 — Run with Docker (optional)

For a production-like stack (API + PostgreSQL + Redis):

```bash
# Generate an encryption key and export it for Docker
export CAREERPILOT_ENCRYPTION_KEY=$(careerpilot generate-encryption-key)

# Build and start all services
docker compose -f docker/docker-compose.yml up --build
```

API: **http://localhost:8000/docs**

Stop with `Ctrl+C`, then `docker compose -f docker/docker-compose.yml down`.

---

### Step 11 — Run tests (verify your setup)

```bash
pytest
```

All tests should pass. They use an isolated in-memory database, so they will not
affect your local `careerpilot.db`.

---

### Recommended first-time workflow (cheat sheet)

Run these in order after setup:

```bash
# 1. Setup (once)
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
careerpilot generate-encryption-key   # paste into .env
careerpilot init-db

# 2. Create profile
careerpilot profile create \
  --name "Your Name" \
  --email "you@example.com" \
  --role "Software Engineer" \
  --skills "Python,SQL,Docker"

# 3. Parse resume into profile (replace path and id)
careerpilot parse-resume /path/to/resume.pdf --profile-id 1

# 4. Discover target companies
careerpilot discover-company "Stripe"
careerpilot discover-company "Anthropic" --remote

# 5. Review results
careerpilot profile show 1
careerpilot profile list
```

---

### Git hooks (optional)

After cloning, install the commit-msg hook once to keep AI co-author trailers out
of git history:

```bash
./scripts/install-git-hooks.sh
```

---

### Troubleshooting

| Problem | Fix |
| ------- | --- |
| `careerpilot: command not found` | Activate `.venv` and re-run `pip install -e ".[dev]"` |
| `Database tables created` never appears | Check Python version: `python3 --version` (need 3.12+) |
| Empty folder in Cursor/VS Code | Open the correct project folder (no trailing space in the name) |
| `CAREERPILOT_ENCRYPTION_KEY` errors in production | Run `careerpilot generate-encryption-key` and set it in `.env` |
| Resume parse returns little data | Try a `.txt` resume first; PDFs with scanned images need OCR (not yet supported) |
| `send-email`, `verify-emails`, etc. say "not implemented" | Those modules are planned — see the Status table below |

---

### What is not available yet

These CLI commands exist as stubs but will show a "coming soon" message:

- `send-email` — send outreach via Gmail/SMTP
- `follow-up` — automated follow-up drafts
- `dashboard` — analytics

The full outreach pipeline (draft → review → send → track) is being built module
by module. Profiles, resume parsing, and company discovery are the starting point.

---

## Quickstart

Requires Python 3.12+ (tested on 3.14).

```bash
# 1. Create a virtualenv and install
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
python -m careerpilot.backend.core.security generate-key   # paste into .env

# 3. Create tables (dev convenience; prod uses Alembic)
careerpilot init-db

# 4. Use the CLI
careerpilot profile create --name "Ada Lovelace" --email ada@example.com \
    --role "Backend Engineer" --skills "Python,Go,SQL"
careerpilot profile list

# 5. Run the API
uvicorn careerpilot.backend.main:app --reload
# Open http://localhost:8000/docs
```

> Default DB is zero-config SQLite. Point `CAREERPILOT_DATABASE_URL` at
> PostgreSQL for production.
>
> For the full walkthrough with examples, see
> [How to Use — Step by Step](#how-to-use--step-by-step) above.


## Testing

```bash
pytest                 # full suite
pytest --cov=careerpilot
```

Tests run against an isolated in-memory SQLite database — hermetic and fast.

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — layers, request flow, design principles
- [Database Schema](docs/DATABASE.md)
- [Configuration & Security](docs/CONFIGURATION.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md) — how to add a module
- [Deployment & Docker](docs/DEPLOYMENT.md)

---

## License

MIT
