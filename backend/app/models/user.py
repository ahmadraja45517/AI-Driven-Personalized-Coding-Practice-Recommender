from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index,
    SmallInteger, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    EnrollmentStatus, PreferredLanguage, StudentLevel,
    pg_enum,
)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    course: Mapped[str] = mapped_column(String(120), nullable=False)
    academic_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("academic_year BETWEEN 1 AND 8", name="academic_year_range"),
        # Email is normalised to lowercase by the service layer; this index is
        # the duplicate-registration guard.
        Index("ix_users_email_lower", func.lower(email), unique=True),
    )

    profile: Mapped["StudentProfile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    enrollments: Mapped[list["RoadmapEnrollment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class StudentProfile(Base, TimestampMixin):
    """Preferences only. Identity/academic data lives on User."""

    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    preferred_language: Mapped[Optional[PreferredLanguage]] = mapped_column(
        pg_enum(PreferredLanguage, "preferred_language")
    )
    # Self-reported. NEVER used as evidence of ability.
    selected_level: Mapped[Optional[StudentLevel]] = mapped_column(
        pg_enum(StudentLevel, "student_level")
    )
    onboarding_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="profile")


class RoadmapEnrollment(Base, TimestampMixin):
    """Explicit opt-in to a roadmap.

    Beginner students are auto-enrolled during onboarding.
    Intermediate/Advanced students are enrolled only if they *choose* the
    Beginner remediation path (Decision 3). Section access requires an ACTIVE
    enrollment AND an UNLOCKED section_unlocks row.
    """

    __tablename__ = "roadmap_enrollments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    roadmap_level: Mapped[StudentLevel] = mapped_column(
        pg_enum(StudentLevel, "student_level"), nullable=False
    )
    status: Mapped[EnrollmentStatus] = mapped_column(
        pg_enum(EnrollmentStatus, "enrollment_status"),
        nullable=False,
        server_default="ACTIVE",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="enrollments")

    __table_args__ = (
        # At most one active enrollment per user.
        Index(
            "uq_roadmap_enrollments_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=(status == EnrollmentStatus.ACTIVE),
        ),
    )