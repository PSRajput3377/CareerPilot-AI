"""User Profile API routes (Module 1)."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from careerpilot.backend.api.dependencies import UserProfileServiceDep
from careerpilot.backend.schemas.user_profile import (
    UserProfileCreate,
    UserProfileRead,
    UserProfileUpdate,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", response_model=UserProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: UserProfileCreate, service: UserProfileServiceDep
) -> UserProfileRead:
    """Create a new user profile with optional nested data."""
    profile = await service.create(payload)
    return UserProfileRead.model_validate(profile)


@router.get("", response_model=list[UserProfileRead])
async def list_profiles(
    service: UserProfileServiceDep,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[UserProfileRead]:
    """List user profiles (paginated)."""
    profiles = await service.list(limit=limit, offset=offset)
    return [UserProfileRead.model_validate(p) for p in profiles]


@router.get("/{profile_id}", response_model=UserProfileRead)
async def get_profile(profile_id: int, service: UserProfileServiceDep) -> UserProfileRead:
    """Fetch a single profile by id."""
    profile = await service.get(profile_id)
    return UserProfileRead.model_validate(profile)


@router.patch("/{profile_id}", response_model=UserProfileRead)
async def update_profile(
    profile_id: int, payload: UserProfileUpdate, service: UserProfileServiceDep
) -> UserProfileRead:
    """Apply a partial update to a profile."""
    profile = await service.update(profile_id, payload)
    return UserProfileRead.model_validate(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(profile_id: int, service: UserProfileServiceDep) -> None:
    """Delete a profile and its children."""
    await service.delete(profile_id)
