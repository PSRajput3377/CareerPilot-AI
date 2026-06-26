"""Email verifier interface and registry (Module 7).

A verifier inspects an email address and returns a deliverability verdict. Two
flavors are anticipated:

* **heuristic** (ships now): offline, deterministic. Checks RFC-ish syntax,
  domain plausibility, a disposable-domain blocklist, and role-account prefixes.
  No network — fully testable.
* **smtp/dns** (future): live MX lookup + SMTP probe via aiosmtplib/dnspython.
  Registers here without changing callers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from careerpilot.backend.schemas.email_verification import VerificationOutcome


class EmailVerifier(ABC):
    """Abstract base for email verifiers."""

    name: str = "abstract"

    @abstractmethod
    async def verify(self, email: str) -> VerificationOutcome:
        """Return a deliverability verdict for ``email``."""
        raise NotImplementedError


def get_verifier(name: str | None = None) -> EmailVerifier:
    """Return a verifier by name, defaulting to the offline heuristic verifier."""
    from careerpilot.backend.services.email_verification.heuristic import (
        HeuristicEmailVerifier,
    )

    requested = (name or "heuristic").lower()
    if requested in {"heuristic", "default", "offline"}:
        return HeuristicEmailVerifier()
    # Future: "smtp" / "dns" verifiers for live checks.
    return HeuristicEmailVerifier()
