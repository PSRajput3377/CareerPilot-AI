"""Email Verification package (Module 7).

Re-exports the service and verifier so callers can import from the package root.
"""

from careerpilot.backend.services.email_verification.base import (
    EmailVerifier,
    get_verifier,
)
from careerpilot.backend.services.email_verification.service import (
    EmailVerificationService,
)

__all__ = ["EmailVerifier", "get_verifier", "EmailVerificationService"]
