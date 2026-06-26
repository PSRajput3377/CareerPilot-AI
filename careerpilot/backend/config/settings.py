"""Application configuration management (Module 19).

Layered configuration:

1. Defaults declared on the Pydantic models below.
2. Non-secret values from ``config.yaml`` (environment-agnostic).
3. Secrets / per-environment overrides from environment variables and ``.env``
   (prefixed with ``CAREERPILOT_``). Environment always wins.

Access the singleton via :func:`get_settings`, which is cached so the YAML file
and environment are read only once per process.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = three levels up from this file: backend/config/settings.py
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


class RateLimitConfig(BaseModel):
    emails_per_hour: int = 30
    emails_per_day: int = 100
    min_seconds_between_sends: int = 45


class RetryConfig(BaseModel):
    max_attempts: int = 3
    backoff_base_seconds: float = 2.0
    backoff_max_seconds: float = 60.0


class SchedulingConfig(BaseModel):
    avoid_weekends: bool = True
    send_window_start: str = "09:00"
    send_window_end: str = "18:00"
    timezone: str = "UTC"
    followup_offsets_days: list[int] = Field(default_factory=lambda: [3, 7, 14])


class LoggingConfig(BaseModel):
    level: str = "INFO"
    directory: str = "careerpilot/backend/logs"


class EmailPatternConfig(BaseModel):
    """Templates for guessing business emails (Module 6).

    Each template uses ``{first} {last} {f} {l}`` placeholders and is rendered
    against the email-safe local parts of a person's name. Order is significance:
    the first usable template is the primary guess.
    """

    max_candidates: int = 6
    templates: list[str] = Field(
        default_factory=lambda: [
            "{first}.{last}",
            "{f}{last}",
            "{first}",
            "{first}{last}",
            "{f}.{last}",
            "{last}.{first}",
            "{last}",
            "{first}_{last}",
        ]
    )


class LLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 1200


def _load_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML config file, returning an empty dict if it is absent."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


class Settings(BaseSettings):
    """Root settings object.

    Secrets and environment-specific values are sourced from the environment
    (``CAREERPILOT_*``); structured non-secret config is hydrated from YAML.
    """

    model_config = SettingsConfigDict(
        env_prefix="CAREERPILOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # ---- Core ----
    env: str = "development"
    debug: bool = True
    app_name: str = "CareerPilot AI"
    app_version: str = "0.1.0"

    # ---- Database ----
    database_url: str = "sqlite+aiosqlite:///./careerpilot.db"

    # ---- Security ----
    # Base64 urlsafe Fernet key. Optional in dev (a transient key is derived),
    # required in production — enforced by ``core.security``.
    encryption_key: str | None = None

    # ---- Secrets pulled from env (used by later modules) ----
    openai_api_key: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None

    # ---- Structured config (from YAML) ----
    rate_limits: RateLimitConfig = Field(default_factory=RateLimitConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    scheduling: SchedulingConfig = Field(default_factory=SchedulingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    email_patterns: EmailPatternConfig = Field(default_factory=EmailPatternConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def is_testing(self) -> bool:
        return self.env.lower() == "testing"


def _build_settings(config_path: Path | None = None) -> Settings:
    """Merge YAML config with environment-sourced settings.

    Environment variables take precedence over YAML for any overlapping key.
    """
    yaml_data = _load_yaml(config_path or DEFAULT_CONFIG_PATH)

    # Map the nested YAML structure onto the flat-ish Settings fields.
    overrides: dict[str, Any] = {}
    if "app" in yaml_data:
        overrides["app_name"] = yaml_data["app"].get("name", "CareerPilot AI")
        overrides["app_version"] = yaml_data["app"].get("version", "0.1.0")
    for key in (
        "rate_limits",
        "retry",
        "scheduling",
        "logging",
        "email_patterns",
        "llm",
    ):
        if key in yaml_data and yaml_data[key] is not None:
            overrides[key] = yaml_data[key]

    # Settings() reads env/.env; YAML values fill structured sections. Env still
    # wins for scalar fields because pydantic-settings applies env after kwargs
    # only for fields not explicitly passed — so we pass only YAML-owned keys.
    return Settings(**overrides)


_CACHED: Settings | None = None


def get_settings() -> Settings:
    """Return the process-wide cached :class:`Settings` instance."""
    global _CACHED
    if _CACHED is None:
        _CACHED = _build_settings()
    return _CACHED


def reload_settings(config_path: Path | None = None) -> Settings:
    """Rebuild and re-cache settings — primarily for tests."""
    global _CACHED
    _CACHED = _build_settings(config_path)
    return _CACHED
