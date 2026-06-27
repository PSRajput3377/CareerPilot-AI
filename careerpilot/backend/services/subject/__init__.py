"""Subject Generator package (Module 11).

Re-exports the generator registry and service so callers can import from the
package root regardless of internal layout.
"""

from careerpilot.backend.services.subject.base import (
    SubjectContext,
    SubjectGenerator,
    get_generator,
)
from careerpilot.backend.services.subject.service import SubjectService

__all__ = [
    "SubjectContext",
    "SubjectGenerator",
    "get_generator",
    "SubjectService",
]
