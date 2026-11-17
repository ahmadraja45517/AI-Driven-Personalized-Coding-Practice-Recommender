from __future__ import annotations

from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, ForeignKey, Index, Numeric,
    SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    ContentSource, Difficulty, LearningItemKind, SectionContentStatus,
    StudentLevel, pg_enum,
)


class Topic(Base, TimestampMixin):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_diagnostic_topic: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (Index("ix_topics_order_index", "order_index"),)


class LearningSection(Base, TimestampMixin):
    __tablename__ = "learning_sections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("topics.id", ondelete="SET NULL")
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    target_level: Mapped[StudentLevel] = mapped_column(
        pg_enum(StudentLevel, "student_level"), nullable=False, server_default="BEGINNER"
    )
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    content_status: Mapped[SectionContentStatus] = mapped_column(
        pg_enum(SectionContentStatus, "section_content_status"),
        nullable=False,
        server_default="PUBLISHED",
    )

    required_completion_ratio: Mapped[float] = mapped_column(
        Numeric(4, 3), nullable=False, server_default="0.800"
    )
    required_assessment_ratio: Mapped[float] = mapped_column(
        Numeric(4, 3), nullable=False, server_default="0.700"
    )

    __table_args__ = (
        CheckConstraint(
            "required_completion_ratio > 0 AND required_completion_ratio <= 1",
            name="completion_ratio_range",
        ),
        CheckConstraint(
            "required_assessment_ratio > 0 AND required_assessment_ratio <= 1",
            name="assessment_ratio_range",
        ),
        UniqueConstraint("target_level", "order_index", name="uq_section_level_order"),
    )


class LearningItem(Base, TimestampMixin):
    __tablename__ = "learning_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[LearningItemKind] = mapped_column(
        pg_enum(LearningItemKind, "learning_item_kind"), nullable=False
    )
    source: Mapped[ContentSource] = mapped_column(
        pg_enum(ContentSource, "content_source"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    content_md: Mapped[Optional[str]] = mapped_column(Text)
    external_url: Mapped[Optional[str]] = mapped_column(String(500))
    difficulty: Mapped[Optional[Difficulty]] = mapped_column(
        pg_enum(Difficulty, "difficulty")
    )
    estimated_minutes: Mapped[Optional[int]] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (
        CheckConstraint(
            "(kind = 'LESSON' AND source = 'INTERNAL' "
            " AND content_md IS NOT NULL AND external_url IS NULL) "
            "OR (kind = 'EXTERNAL_PROBLEM' AND source = 'LEETCODE' "
            " AND external_url IS NOT NULL AND content_md IS NULL "
            " AND external_url LIKE 'https://leetcode.com/%')",
            name="lesson_or_problem_shape",
        ),
        Index("ix_learning_items_topic_difficulty", "topic_id", "difficulty"),
    )


class SectionItem(Base):
    __tablename__ = "section_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("learning_sections.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("learning_items.id", ondelete="CASCADE"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    item: Mapped["LearningItem"] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint("section_id", "item_id", name="uq_section_item"),
        UniqueConstraint("section_id", "order_index", name="uq_section_item_order"),
    )