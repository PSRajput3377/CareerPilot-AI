"""Career Page Detection package (Module 4).

Re-exports the service so callers can import from the package root regardless of
internal layout.
"""

from careerpilot.backend.services.career_page.service import (
    CareerPageService,
    detection_summary,
)

__all__ = ["CareerPageService", "detection_summary"]
