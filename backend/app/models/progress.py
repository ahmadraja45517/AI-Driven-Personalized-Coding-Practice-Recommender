from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import UnlockStatus, pg_enum


class StudentProgress(Base):
    """Self-reported completion of a learning item. Never verified."""

    __tablename__ = "student_progress"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("learning_items.id", ondelete="CASCADE"), nullable=False
    )
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    first_opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # v1: always true. Kept so a future verified source cannot be confused
    # with a student's own checkbox.
    self_reported: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=__import__("sqlalchemy").func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_progress_user_item"),
        CheckConstraint(
            "(is_completed = false AND completed_at IS NULL) OR is_completed = true",
            name="completed_at_requires_completion",
        ),
        Index("ix_student_progress_user_completed", "user_id", "is_completed"),
    )


class SectionUnlock(Base):
    """Persistent unlock/completion state of one section for one student."""

    __tablename__ = "section_unlocks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("learning_sections.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[UnlockStatus] = mapped_column(
        pg_enum(UnlockStatus, "unlock_status"), nullable=False, server_default="LOCKED"
    )
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Audit: which passing attempt satisfied the gate.
    unlocked_by_attempt_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("assessment_attempts.id", ondelete="SET NULL")
    )
    # Snapshot of the completion ratio at the moment of unlock.
    completion_ratio: Mapped[Optional[float]] = mapped_column(Numeric(5, 4))

    __table_args__ = (
        UniqueConstraint("user_id", "section_id", name="uq_section_unlock"),
        Index("ix_section_unlocks_user_status", "user_id", "status"),
    )