# Configuration & Security (Modules 19 & 20)

## Layered configuration

Settings resolve in this precedence order (later wins):

1. Field defaults in `config/settings.py`.
2. `config.yaml` — non-secret, environment-agnostic structure (rate limits,
   retry, scheduling, logging, LLM behaviour).
3. Environment variables / `.env`, prefixed `CAREERPILOT_` — secrets and
   per-environment overrides.

Access via `get_settings()` (cached). Tests use `reload_settings()`.

### Why this split?

Secrets must never live in version-controlled files. `config.yaml` is safe to
commit; `.env` is git-ignored. Structured behaviour (e.g. `followup_offsets_days`)
belongs in YAML where it is reviewable and diffable.

## Secrets & encryption (Module 20)

- Credentials (SMTP password, API keys, DB URL) come from the environment only.
- Secrets persisted to the database (e.g. a user's SMTP password for sending)
  are encrypted at rest with **Fernet** (`core/security.py`).

Generate an encryption key:

```bash
python -m careerpilot.backend.core.security generate-key
# or
careerpilot generate-encryption-key
```

Put it in `.env` as `CAREERPILOT_ENCRYPTION_KEY`. In **production this is
mandatory** — `core.security` raises if it is missing. In development a
process-ephemeral key is derived so the app runs without setup (such data does
not survive a restart, which is intentional).

```python
from careerpilot.backend.core.security import get_cipher

cipher = get_cipher()
token = cipher.encrypt("smtp-password")   # store `token`
plain = cipher.decrypt(token)             # at send time
```

## Key environment variables

| Variable | Purpose |
| -------- | ------- |
| `CAREERPILOT_ENV` | `development` \| `testing` \| `production` |
| `CAREERPILOT_DATABASE_URL` | Async DB URL |
| `CAREERPILOT_ENCRYPTION_KEY` | Fernet key (required in prod) |
| `CAREERPILOT_OPENAI_API_KEY` | LLM provider key |
| `CAREERPILOT_SMTP_*` | SMTP credentials |

See `.env.example` for the full list.
