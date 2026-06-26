"""User Profile ORM models (Module 1).

A :class:`UserProfile` is the root aggregate. Skills, experience, and education
are modeled as child rows so they can be queried and updated independently and
so later modules (Resume Parser, Job Matching) can populate them structurally.
"""

from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from careerpilot.backend.database.base import Base, TimestampMixin


class WorkAuthorization(enum.StrEnum):
    """Work authorization status options."""

    CITIZEN = "citizen"
    PERMANENT_RESIDENT = "permanent_resident"
    WORK_VISA = "work_visa"
    STUDENT_VISA = "student_visa"
    NEEDS_SPONSORSHIP = "needs_sponsorship"
    OTHER = "other"


class UserProfile(Base, TimestampMixin):
    """Root profile aggregate for a CareerPilot user."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identity & links
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    resume_path: Mapped[str | None] = mapped_column(String(1024))
    github_url: Mapped[str | None] = mapped_column(String(512))
    portfolio_url: Mapped[str | None] = mapped_column(String(512))
    linkedin_url: Mapped[str | None] = mapped_column(String(512))

    # Preferences
    preferred_role: Mapped[str | None] = mapped_column(String(255))
    preferred_location: Mapped[str | None] = mapped_column(String(255))
    work_authorization: Mapped[WorkAuthorization | None] = mapped_column(
        Enum(WorkAuthorization, native_enum=False, length=32)
    )
    preferred_companies: Mapped[str | None] = mapped_column(Text)  # comma-separated
    preferred_salary_min: Mapped[int | None] = mapped_column(Integer)
    preferred_salary_max: Mapped[int | None] = mapped_column(Integer)
    availability: Mapped[str | None] = mapped_column(String(255))

    # Children
    skills: Mapped[list[Skill]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )
    experiences: Mapped[list[Experience]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )
    educations: Mapped[list[Education]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )
    projects: Mapped[list[Project]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )
    achievements: Mapped[list[Achievement]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )


class Skill(Base):
    """A single skill attached to a profile."""

    __tablename__ = "profile_skills"
    __table_args__ = (UniqueConstraint("profile_id", "name", name="uq_profile_skill"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    proficiency: Mapped[str | None] = mapped_column(String(32))  # e.g. beginner/expert
    years: Mapped[float | None] = mapped_column(Float)

    profile: Mapped[UserProfile] = relationship(back_populates="skills")


class Experience(Base):
    """A work experience entry."""

    __tablename__ = "profile_experiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)  # null = current
    description: Mapped[str | None] = mapped_column(Text)
    is_internship: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile: Mapped[UserProfile] = relationship(back_populates="experiences")


class Education(Base):
    """An education entry."""

    __tablename__ = "profile_educations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str | None] = mapped_column(String(255))
    field_of_study: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    grade: Mapped[str | None] = mapped_column(String(64))

    profile: Mapped[UserProfile] = relationship(back_populates="educations")


class Project(Base):
    """A project entry (often extracted from a resume by Module 2)."""

    __tablename__ = "profile_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tech_stack: Mapped[str | None] = mapped_column(Text)  # comma-separated
    url: Mapped[str | None] = mapped_column(String(512))

    profile: Mapped[UserProfile] = relationship(back_populates="projects")


class Achievement(Base):
    """An achievement / award entry."""

    __tablename__ = "profile_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)

    profile: Mapped[UserProfile] = relationship(back_populates="achievements")
