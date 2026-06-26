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
| 2 | Resume Parser | ⏳ Planned |
| 3 | Company Discovery | ⏳ Planned |
| 4 | Career Page Detection | ⏳ Planned |
| 5 | People Discovery | ⏳ Planned |
| 6 | Email Pattern Generator | ⏳ Planned |
| 7 | Email Verification | ⏳ Planned |
| 8 | Job Matching AI | ⏳ Planned |
| 9 | Cover Letter Generator | ⏳ Planned |
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

---

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
