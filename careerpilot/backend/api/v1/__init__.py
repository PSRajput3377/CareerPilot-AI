"""API v1 router aggregation.

Feature routers are included here; new modules register their router in this
one place so ``main.py`` stays stable as the platform grows.
"""

from fastapi import APIRouter

from careerpilot.backend.api.v1 import (
    companies,
    email_patterns,
    people,
    profiles,
    resumes,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(profiles.router)
api_router.include_router(resumes.router)
api_router.include_router(companies.router)
api_router.include_router(people.router)
api_router.include_router(email_patterns.router)

__all__ = ["api_router"]
