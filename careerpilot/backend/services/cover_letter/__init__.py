"""Cover Letter Generator package (Module 9).

Re-exports the generator registry and service so callers can import from the
package root regardless of internal layout.
"""

from careerpilot.backend.services.cover_letter.base import (
    CoverLetterContext,
    CoverLetterGenerator,
    get_generator,
)
from careerpilot.backend.services.cover_letter.service import CoverLetterService

__all__ = [
    "CoverLetterContext",
    "CoverLetterGenerator",
    "get_generator",
    "CoverLetterService",
]
