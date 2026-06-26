"""ORM model registry.

Importing this package ensures all models are registered on ``Base.metadata``
(needed for ``create_all`` and Alembic autogenerate).
"""

from careerpilot.backend.models.company import (
    Company,
    FundingStage,
    HiringStatus,
)
from careerpilot.backend.models.user_profile import (
    Achievement,
    Education,
    Experience,
    Project,
    Skill,
    UserProfile,
    WorkAuthorization,
)

__all__ = [
    "UserProfile",
    "Skill",
    "Experience",
    "Education",
    "Project",
    "Achievement",
    "WorkAuthorization",
    "Company",
    "FundingStage",
    "HiringStatus",
]
