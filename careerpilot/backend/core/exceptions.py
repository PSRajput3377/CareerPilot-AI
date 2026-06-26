"""Domain exception hierarchy.

Service/repository layers raise these provider-agnostic errors; the API layer
maps them to HTTP responses (see ``api.errors``), keeping HTTP concerns out of
the business logic.
"""

from __future__ import annotations


class CareerPilotError(Exception):
    """Base class for all application errors."""


class NotFoundError(CareerPilotError):
    """A requested entity does not exist."""


class ConflictError(CareerPilotError):
    """The operation conflicts with existing state (e.g. duplicate)."""


class ValidationError(CareerPilotError):
    """Input failed a business-rule validation (beyond schema validation)."""
