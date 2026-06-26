"""Email Pattern Generator package (Module 6).

Re-exports the generator and service so callers can import from the package root
regardless of internal layout.
"""

from careerpilot.backend.services.email_pattern.generator import (
    EmailPatternGenerator,
)
from careerpilot.backend.services.email_pattern.service import EmailPatternService

__all__ = ["EmailPatternGenerator", "EmailPatternService"]
