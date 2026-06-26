"""Offline heuristic email verifier (Module 7).

Deterministic deliverability checks that need no network, so the pipeline is
fully testable:

* **syntax** — a pragmatic RFC-5322-ish regex (one ``@``, sane local/domain).
* **domain** — must have a dot, a plausible TLD, and no obvious typos.
* **mx** — approximated from a small set of well-known mail domains plus the
  presence of a valid public-suffix-looking TLD (a real verifier swaps this for
  a DNS MX lookup).
* **disposable** — blocklist of throwaway-email providers → RISKY.
* **role account** — generic mailboxes (info@, support@, …) → RISKY.

A real SMTP/DNS verifier registers via the base registry without changing the
service. Verdicts feed the ``verify deliverability`` gate: only ``VALID`` lets a
person's ``email_verified`` flag be set.
"""

from __future__ import annotations

import re

from careerpilot.backend.models.email_verification import VerificationStatus
from careerpilot.backend.schemas.email_verification import VerificationOutcome
from careerpilot.backend.services.email_verification.base import EmailVerifier

# Pragmatic syntax check — not a full RFC parser, but rejects the common junk.
_SYNTAX = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
)

# Throwaway / disposable email providers — deliverable but untrustworthy.
_DISPOSABLE_DOMAINS = frozenset(
    {
        "mailinator.com",
        "guerrillamail.com",
        "10minutemail.com",
        "tempmail.com",
        "trashmail.com",
        "yopmail.com",
        "throwawaymail.com",
        "getnada.com",
        "sharklasers.com",
        "dispostable.com",
    }
)

# Generic role mailboxes — not a specific person, discouraged for outreach.
_ROLE_PREFIXES = frozenset(
    {
        "info",
        "support",
        "sales",
        "admin",
        "contact",
        "help",
        "billing",
        "hello",
        "team",
        "office",
        "noreply",
        "no-reply",
        "careers",
        "jobs",
        "hr",
    }
)

# A few domains we treat as definitely mail-accepting without a DNS lookup.
_KNOWN_MAIL_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "outlook.com",
        "hotmail.com",
        "yahoo.com",
        "icloud.com",
        "protonmail.com",
        "fastmail.com",
    }
)


class HeuristicEmailVerifier(EmailVerifier):
    """Deterministic offline deliverability heuristics."""

    name = "heuristic"

    async def verify(self, email: str) -> VerificationOutcome:
        email = (email or "").strip()
        outcome = VerificationOutcome(email=email, verifier=self.name)

        if not email:
            outcome.status = VerificationStatus.UNKNOWN
            outcome.reason = "No email to verify."
            return outcome

        outcome.syntax_ok = bool(_SYNTAX.match(email))
        if not outcome.syntax_ok:
            outcome.status = VerificationStatus.INVALID
            outcome.confidence = 0.95
            outcome.reason = "Malformed address (failed syntax check)."
            return outcome

        local, _, domain = email.partition("@")
        local = local.lower()
        domain = domain.lower()

        outcome.domain_ok = self._domain_ok(domain)
        if not outcome.domain_ok:
            outcome.status = VerificationStatus.INVALID
            outcome.confidence = 0.8
            outcome.reason = "Domain is not a plausible mail domain."
            return outcome

        outcome.mx_found = self._mx_found(domain)
        outcome.is_disposable = domain in _DISPOSABLE_DOMAINS
        outcome.is_role_account = local.split("+")[0] in _ROLE_PREFIXES

        return self._verdict(outcome)

    # -- internals --------------------------------------------------------- #

    def _domain_ok(self, domain: str) -> bool:
        if "." not in domain or domain.startswith(".") or domain.endswith("."):
            return False
        if ".." in domain:
            return False
        tld = domain.rsplit(".", 1)[-1]
        return len(tld) >= 2 and tld.isalpha()

    def _mx_found(self, domain: str) -> bool:
        # Offline approximation: known mail domains, or any well-formed domain
        # (a real verifier replaces this with a DNS MX query).
        return domain in _KNOWN_MAIL_DOMAINS or self._domain_ok(domain)

    def _verdict(self, outcome: VerificationOutcome) -> VerificationOutcome:
        if outcome.is_disposable:
            outcome.status = VerificationStatus.RISKY
            outcome.confidence = 0.7
            outcome.reason = "Disposable email domain."
            return outcome
        if outcome.is_role_account:
            outcome.status = VerificationStatus.RISKY
            outcome.confidence = 0.6
            outcome.reason = "Role/generic mailbox, not an individual."
            return outcome
        if outcome.mx_found:
            outcome.status = VerificationStatus.VALID
            outcome.confidence = 0.75
            outcome.reason = "Valid syntax and mail-accepting domain."
            return outcome

        outcome.status = VerificationStatus.UNKNOWN
        outcome.confidence = 0.3
        outcome.reason = "Could not confirm a mail server for the domain."
        return outcome
