"""AI Personalization Engine package (Module 12).

Re-exports the engine registry and service so callers can import from the
package root regardless of internal layout.
"""

from careerpilot.backend.services.personalization.base import (
    PersonalizationContext,
    PersonalizationEngine,
    get_engine,
)
from careerpilot.backend.services.personalization.service import (
    PersonalizationService,
)

__all__ = [
    "PersonalizationContext",
    "PersonalizationEngine",
    "get_engine",
    "PersonalizationService",
]
