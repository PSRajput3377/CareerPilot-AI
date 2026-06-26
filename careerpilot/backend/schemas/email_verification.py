"""Schemas for Email Verification (Module 7)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from careerpilot.backend.models.email_verification import VerificationStatus


class VerificationOutcome(BaseModel):
    """A verifier's verdict for a single address (provider-agnostic, no DB)."""

    email: str
    status: VerificationStatus = VerificationStatus.UNKNOWN
    syntax_ok: bool = False
    domain_ok: bool = False
    mx_found: bool = False
    is_disposable: bool = False
    is_role_account: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str | None = None
    verifier: str = "unknown"

    @property
    def is_valid(self) -> bool:
        """True when the address passed the deliverability gate."""
        return self.status == VerificationStatus.VALID


class EmailVerificationRead(BaseModel):
    """A persisted verification record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    person_id: int
    email: str
    status: VerificationStatus
    syntax_ok: bool
    domain_ok: bool
    mx_found: bool
    is_disposable: bool
    is_role_account: bool
    confidence: float
    reason: str | None = None
    verifier: str | None = None
    created_at: datetime
    updated_at: datetime


class PersonVerificationResult(BaseModel):
    """Outcome of verifying a stored person's email (Module 7)."""

    person_id: int
    outcome: VerificationOutcome
    #: Whether ``person.email_verified`` was set true by this run.
    email_verified: bool = False
