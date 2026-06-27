"""Job Matching package (Module 8).

Re-exports the matcher registry and service so callers can import from the
package root regardless of internal layout.
"""

from careerpilot.backend.services.job_matching.base import JobMatcher, get_matcher
from careerpilot.backend.services.job_matching.service import JobMatchingService

__all__ = ["JobMatcher", "get_matcher", "JobMatchingService"]
