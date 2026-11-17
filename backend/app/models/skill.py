from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Numeric,
    SmallInteger, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    Difficulty, RecommendationKind, RecommendationStatus,
    SkillTopicClassification, SkillTrend, StudentLevel, pg_enum,
)


class SkillProfile(Base):
    """Immutable snapshot; the newest one carries is_current = true."""

    __tablename__ = "student_skill_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    # Kept separate from StudentProfile.selected_level by design.
    demonstrated_level: Mapped[Optional[StudentLevel]] = mapped_column(
        pg_enum(StudentLevel, "student_level")
    )
    recommended_level: Mapped[Optional[StudentLevel]] = mapped_column(
        pg_enum(StudentLevel, "student_level")
    )
    overall_accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    evidence_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    topics: Mapped[list["SkillProfileTopic"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # At most one current snapshot per user; history is preserved.
        Index(
            "uq_skill_profiles_one_current",
            "user_id",
            unique=True,
            postgresql_where=(is_current.is_(True)),
        ),
    )


class SkillProfileTopic(Base):
    __tablename__ = "student_skill_profile_topics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    skill_profile_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("student_skill_profiles.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    previous_accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    evidence_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    # Derived from accuracy per Decision 6B (<40% -> EASY, 40-69% -> MEDIUM, >=70% -> HARD).
    target_difficulty: Mapped[Optional[Difficulty]] = mapped_column(pg_enum(Difficulty, "difficulty"))
    classification: Mapped[SkillTopicClassification] = mapped_column(
        pg_enum(SkillTopicClassification, "skill_topic_classification"),
        nullable=False,
        server_default="INSUFFICIENT_DATA",
    )
    trend: Mapped[SkillTrend] = mapped_column(
        pg_enum(SkillTrend, "skill_trend"), nullable=False, server_default="STABLE"
    )

    profile: Mapped["SkillProfile"] = relationship(back_populates="topics")

    __table_args__ = (
        UniqueConstraint("skill_profile_id", "topic_id", name="uq_profile_topic"),
        CheckConstraint(
            "accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 1)", name="accuracy_range"
        ),
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Which skill snapshot produced this row (reproducibility).
    skill_profile_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("student_skill_profiles.id", ondelete="SET NULL")
    )
    topic_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    # A recommendation targets a section (remediation path) or a specific item.
    section_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("learning_sections.id", ondelete="CASCADE")
    )
    item_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("learning_items.id", ondelete="CASCADE")
    )

    kind: Mapped[RecommendationKind] = mapped_column(
        pg_enum(RecommendationKind, "recommendation_kind"), nullable=False
    )
    status: Mapped[RecommendationStatus] = mapped_column(
        pg_enum(RecommendationStatus, "recommendation_status"),
        nullable=False,
        server_default="ACTIVE",
    )

    # R = 0.40W + 0.35D + 0.25P. Components stored for explainability.
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    weak_topic_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)   # W
    difficulty_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)   # D
    prerequisite_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False) # P

    target_difficulty: Mapped[Optional[Difficulty]] = mapped_column(pg_enum(Difficulty, "difficulty"))
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("item_id IS NOT NULL OR section_id IS NOT NULL", name="target_present"),
        CheckConstraint(
            "score >= 0 AND score <= 1 AND weak_topic_score >= 0 AND weak_topic_score <= 1 "
            "AND difficulty_score >= 0 AND difficulty_score <= 1 "
            "AND prerequisite_score >= 0 AND prerequisite_score <= 1",
            name="score_range",
        ),
        Index("ix_recommendations_user_status_score", "user_id", "status", score.desc()),
        # Only one ACTIVE recommendation per (user, item).
        Index(
            "uq_recommendations_active_per_item",
            "user_id", "item_id",
            unique=True,
            postgresql_where=(status == RecommendationStatus.ACTIVE) & (item_id.isnot(None)),
        ),
    )