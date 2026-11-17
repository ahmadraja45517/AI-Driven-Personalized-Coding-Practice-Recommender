from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Numeric,
    SmallInteger, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    AssessmentKind, AttemptStatus, Difficulty, StudentLevel, pg_enum,
)


class Assessment(Base, TimestampMixin):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[AssessmentKind] = mapped_column(
        pg_enum(AssessmentKind, "assessment_kind"), nullable=False
    )
    # DIAGNOSTIC -> target_level set, section_id NULL
    target_level: Mapped[Optional[StudentLevel]] = mapped_column(
        pg_enum(StudentLevel, "student_level")
    )
    # SECTION_END -> section_id set, target_level NULL
    section_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("learning_sections.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(__import__("sqlalchemy").String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    total_marks: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    pass_ratio: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, server_default="0.700")
    duration_minutes: Mapped[Optional[int]] = mapped_column(SmallInteger)
    version: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    questions: Mapped[list["AssessmentQuestion"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan",
        order_by="AssessmentQuestion.order_index",
    )

    __table_args__ = (
        CheckConstraint(
            "(kind = 'DIAGNOSTIC' AND target_level IS NOT NULL AND section_id IS NULL "
            " AND target_level IN ('INTERMEDIATE','ADVANCED')) "
            "OR (kind = 'SECTION_END' AND section_id IS NOT NULL AND target_level IS NULL)",
            name="assessment_kind_shape",
        ),
        CheckConstraint("pass_ratio > 0 AND pass_ratio <= 1", name="pass_ratio_range"),
        # Exactly one active diagnostic per level, and one active end test per section.
        Index(
            "uq_assessments_one_active_diagnostic",
            "target_level",
            unique=True,
            postgresql_where=(kind == AssessmentKind.DIAGNOSTIC) & (is_active.is_(True)),
        ),
        Index(
            "uq_assessments_one_active_section_end",
            "section_id",
            unique=True,
            postgresql_where=(kind == AssessmentKind.SECTION_END) & (is_active.is_(True)),
        ),
    )


class AssessmentQuestion(Base):
    """Bank rows are owned by one assessment, satisfying 'separate banks'."""

    __tablename__ = "assessment_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False
    )
    difficulty: Mapped[Difficulty] = mapped_column(pg_enum(Difficulty, "difficulty"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Never serialised to the client before submission.
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    marks: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    assessment: Mapped["Assessment"] = relationship(back_populates="questions")
    options: Mapped[list["AssessmentOption"]] = relationship(
        back_populates="question", cascade="all, delete-orphan",
        order_by="AssessmentOption.order_index",
    )

    __table_args__ = (
        UniqueConstraint("assessment_id", "order_index", name="uq_question_order"),
        Index("ix_assessment_questions_assessment_topic", "assessment_id", "topic_id"),
    )


class AssessmentOption(Base):
    __tablename__ = "assessment_options"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assessment_questions.id", ondelete="CASCADE"), nullable=False
    )
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0..3 -> A..D

    question: Mapped["AssessmentQuestion"] = relationship(back_populates="options")

    __table_args__ = (
        UniqueConstraint("question_id", "order_index", name="uq_option_order"),
        CheckConstraint("order_index BETWEEN 0 AND 3", name="option_index_range"),
        # Exactly one correct option per question — enforced by the DB.
        Index(
            "uq_assessment_options_one_correct",
            "question_id",
            unique=True,
            postgresql_where=(is_correct.is_(True)),
        ),
    )


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assessment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[AttemptStatus] = mapped_column(
        pg_enum(AttemptStatus, "attempt_status"), nullable=False, server_default="IN_PROGRESS"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    score_marks: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    total_marks: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    passed: Mapped[Optional[bool]] = mapped_column(Boolean)

    answers: Mapped[list["AssessmentAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "assessment_id", "attempt_number", name="uq_attempt_number"),
        CheckConstraint(
            "(status = 'SUBMITTED') = (submitted_at IS NOT NULL)",
            name="submitted_at_consistent",
        ),
        Index("ix_attempts_user_assessment", "user_id", "assessment_id", "submitted_at"),
    )


class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assessment_questions.id", ondelete="CASCADE"), nullable=False
    )
    selected_option_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("assessment_options.id", ondelete="SET NULL")
    )
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)  # NULL until graded
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    attempt: Mapped["AssessmentAttempt"] = relationship(back_populates="answers")

    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_answer_per_question"),
    )


class AttemptTopicResult(Base):
    """Per-attempt, per-topic breakdown. Drives topic-wise reports and skill profiles."""

    __tablename__ = "attempt_topic_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    questions_total: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    questions_correct: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    marks_total: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    marks_obtained: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    accuracy: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)  # 0.0000 - 1.0000

    __table_args__ = (
        UniqueConstraint("attempt_id", "topic_id", name="uq_attempt_topic"),
    )