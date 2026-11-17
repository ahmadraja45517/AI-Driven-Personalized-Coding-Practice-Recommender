"""initial schema

Revision ID: 0001_initial
Revises:
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

ENUMS: dict[str, tuple[str, ...]] = {
    "preferred_language": ("JAVA", "CPP", "PYTHON"),
    "student_level": ("BEGINNER", "INTERMEDIATE", "ADVANCED"),
    "difficulty": ("EASY", "MEDIUM", "HARD"),
    "learning_item_kind": ("LESSON", "EXTERNAL_PROBLEM"),
    "content_source": ("INTERNAL", "LEETCODE"),
    "section_content_status": ("PUBLISHED", "PLANNED"),
    "assessment_kind": ("DIAGNOSTIC", "SECTION_END"),
    "attempt_status": ("IN_PROGRESS", "SUBMITTED", "ABANDONED"),
    "skill_topic_classification": (
        "STRONG", "WEAK", "NEEDS_REVISION", "IMPROVING", "STRUGGLING", "INSUFFICIENT_DATA",
    ),
    "skill_trend": ("IMPROVING", "STABLE", "DECLINING"),
    "recommendation_kind": ("ACTIONABLE", "LOCKED_PREVIEW", "REVISION"),
    "recommendation_status": ("ACTIVE", "DISMISSED", "COMPLETED", "EXPIRED"),
    "unlock_status": ("LOCKED", "UNLOCKED", "COMPLETED"),
    "enrollment_status": ("ACTIVE", "COMPLETED", "ABANDONED"),
}


def E(name: str) -> postgresql.ENUM:
    """Reference an already-created PG enum type without re-creating it."""
    return postgresql.ENUM(*ENUMS[name], name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    for name, values in ENUMS.items():
        postgresql.ENUM(*values, name=name).create(bind, checkfirst=True)

    # ---------------------------------------------------------------- users
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("course", sa.String(120), nullable=False),
        sa.Column("academic_year", sa.SmallInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("academic_year BETWEEN 1 AND 8", name="ck_users_academic_year_range"),
    )
    op.create_index("ix_users_email_lower", "users", [sa.text("lower(email)")], unique=True)

    # --------------------------------------------------------------- topics
    op.create_table(
        "topics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_diagnostic_topic", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_topics"),
        sa.UniqueConstraint("code", name="uq_topics_code"),
    )
    op.create_index("ix_topics_order_index", "topics", ["order_index"])

    # ------------------------------------------------------ student_profiles
    op.create_table(
        "student_profiles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("preferred_language", E("preferred_language"), nullable=True),
        sa.Column("selected_level", E("student_level"), nullable=True),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_student_profiles"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_student_profiles_user_id_users", ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_student_profiles_user_id"),
    )

    # ----------------------------------------------------- learning_sections
    op.create_table(
        "learning_sections",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("topic_id", sa.BigInteger(), nullable=True),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_level", E("student_level"), server_default="BEGINNER", nullable=False),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.Column("content_status", E("section_content_status"), server_default="PUBLISHED", nullable=False),
        sa.Column("required_completion_ratio", sa.Numeric(4, 3), server_default="0.800", nullable=False),
        sa.Column("required_assessment_ratio", sa.Numeric(4, 3), server_default="0.700", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_learning_sections"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name="fk_learning_sections_topic_id_topics", ondelete="SET NULL"),
        sa.UniqueConstraint("slug", name="uq_learning_sections_slug"),
        sa.UniqueConstraint("target_level", "order_index", name="uq_section_level_order"),
        sa.CheckConstraint("required_completion_ratio > 0 AND required_completion_ratio <= 1", name="ck_learning_sections_completion_ratio_range"),
        sa.CheckConstraint("required_assessment_ratio > 0 AND required_assessment_ratio <= 1", name="ck_learning_sections_assessment_ratio_range"),
    )

    # -------------------------------------------------------- learning_items
    op.create_table(
        "learning_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("topic_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", E("learning_item_kind"), nullable=False),
        sa.Column("source", E("content_source"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_md", sa.Text(), nullable=True),
        sa.Column("external_url", sa.String(500), nullable=True),
        sa.Column("difficulty", E("difficulty"), nullable=True),
        sa.Column("estimated_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_learning_items"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name="fk_learning_items_topic_id_topics", ondelete="RESTRICT"),
        sa.CheckConstraint(
            "(kind = 'LESSON' AND source = 'INTERNAL' AND content_md IS NOT NULL AND external_url IS NULL) "
            "OR (kind = 'EXTERNAL_PROBLEM' AND source = 'LEETCODE' AND external_url IS NOT NULL "
            "AND content_md IS NULL AND external_url LIKE 'https://leetcode.com/%')",
            name="ck_learning_items_lesson_or_problem_shape",
        ),
    )
    op.create_index("ix_learning_items_topic_difficulty", "learning_items", ["topic_id", "difficulty"])

    # ---------------------------------------------------------- section_items
    op.create_table(
        "section_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("section_id", sa.BigInteger(), nullable=False),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_section_items"),
        sa.ForeignKeyConstraint(["section_id"], ["learning_sections.id"], name="fk_section_items_section_id_learning_sections", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["learning_items.id"], name="fk_section_items_item_id_learning_items", ondelete="CASCADE"),
        sa.UniqueConstraint("section_id", "item_id", name="uq_section_item"),
        sa.UniqueConstraint("section_id", "order_index", name="uq_section_item_order"),
    )

    # ------------------------------------------------------------ assessments
    op.create_table(
        "assessments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kind", E("assessment_kind"), nullable=False),
        sa.Column("target_level", E("student_level"), nullable=True),
        sa.Column("section_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("total_marks", sa.SmallInteger(), nullable=False),
        sa.Column("pass_ratio", sa.Numeric(4, 3), server_default="0.700", nullable=False),
        sa.Column("duration_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("version", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_assessments"),
        sa.ForeignKeyConstraint(["section_id"], ["learning_sections.id"], name="fk_assessments_section_id_learning_sections", ondelete="CASCADE"),
        sa.CheckConstraint(
            "(kind = 'DIAGNOSTIC' AND target_level IS NOT NULL AND section_id IS NULL "
            "AND target_level IN ('INTERMEDIATE','ADVANCED')) "
            "OR (kind = 'SECTION_END' AND section_id IS NOT NULL AND target_level IS NULL)",
            name="ck_assessments_assessment_kind_shape",
        ),
        sa.CheckConstraint("pass_ratio > 0 AND pass_ratio <= 1", name="ck_assessments_pass_ratio_range"),
    )
    op.create_index(
        "uq_assessments_one_active_diagnostic", "assessments", ["target_level"], unique=True,
        postgresql_where=sa.text("kind = 'DIAGNOSTIC' AND is_active"),
    )
    op.create_index(
        "uq_assessments_one_active_section_end", "assessments", ["section_id"], unique=True,
        postgresql_where=sa.text("kind = 'SECTION_END' AND is_active"),
    )

    # --------------------------------------------------- assessment_questions
    op.create_table(
        "assessment_questions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("assessment_id", sa.BigInteger(), nullable=False),
        sa.Column("topic_id", sa.BigInteger(), nullable=False),
        sa.Column("difficulty", E("difficulty"), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("marks", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_assessment_questions"),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], name="fk_assessment_questions_assessment_id_assessments", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name="fk_assessment_questions_topic_id_topics", ondelete="RESTRICT"),
        sa.UniqueConstraint("assessment_id", "order_index", name="uq_question_order"),
    )
    op.create_index("ix_assessment_questions_assessment_topic", "assessment_questions", ["assessment_id", "topic_id"])

    # ----------------------------------------------------- assessment_options
    op.create_table(
        "assessment_options",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("option_text", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_assessment_options"),
        sa.ForeignKeyConstraint(["question_id"], ["assessment_questions.id"], name="fk_assessment_options_question_id_assessment_questions", ondelete="CASCADE"),
        sa.UniqueConstraint("question_id", "order_index", name="uq_option_order"),
        sa.CheckConstraint("order_index BETWEEN 0 AND 3", name="ck_assessment_options_option_index_range"),
    )
    op.create_index(
        "uq_assessment_options_one_correct", "assessment_options", ["question_id"], unique=True,
        postgresql_where=sa.text("is_correct"),
    )

    # --------------------------------------------------- roadmap_enrollments
    op.create_table(
        "roadmap_enrollments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("roadmap_level", E("student_level"), nullable=False),
        sa.Column("status", E("enrollment_status"), server_default="ACTIVE", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_roadmap_enrollments"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_roadmap_enrollments_user_id_users", ondelete="CASCADE"),
    )
    op.create_index(
        "uq_roadmap_enrollments_one_active_per_user", "roadmap_enrollments", ["user_id"], unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    # ------------------------------------------------------- student_progress
    op.create_table(
        "student_progress",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("self_reported", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_student_progress"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_student_progress_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["learning_items.id"], name="fk_student_progress_item_id_learning_items", ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "item_id", name="uq_progress_user_item"),
        sa.CheckConstraint(
            "(is_completed = false AND completed_at IS NULL) OR is_completed = true",
            name="ck_student_progress_completed_at_requires_completion",
        ),
    )
    op.create_index("ix_student_progress_user_completed", "student_progress", ["user_id", "is_completed"])

    # ---------------------------------------------------- assessment_attempts
    op.create_table(
        "assessment_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("assessment_id", sa.BigInteger(), nullable=False),
        sa.Column("attempt_number", sa.SmallInteger(), nullable=False),
        sa.Column("status", E("attempt_status"), server_default="IN_PROGRESS", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score_marks", sa.Numeric(6, 2), nullable=True),
        sa.Column("total_marks", sa.Numeric(6, 2), nullable=True),
        sa.Column("percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_assessment_attempts"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_assessment_attempts_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], name="fk_assessment_attempts_assessment_id_assessments", ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "assessment_id", "attempt_number", name="uq_attempt_number"),
        sa.CheckConstraint(
            "(status = 'SUBMITTED') = (submitted_at IS NOT NULL)",
            name="ck_assessment_attempts_submitted_at_consistent",
        ),
    )
    op.create_index("ix_attempts_user_assessment", "assessment_attempts", ["user_id", "assessment_id", "submitted_at"])

    # ----------------------------------------------------- assessment_answers
    op.create_table(
        "assessment_answers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("attempt_id", sa.BigInteger(), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("selected_option_id", sa.BigInteger(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_assessment_answers"),
        sa.ForeignKeyConstraint(["attempt_id"], ["assessment_attempts.id"], name="fk_assessment_answers_attempt_id_assessment_attempts", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["assessment_questions.id"], name="fk_assessment_answers_question_id_assessment_questions", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selected_option_id"], ["assessment_options.id"], name="fk_assessment_answers_selected_option_id_assessment_options", ondelete="SET NULL"),
        sa.UniqueConstraint("attempt_id", "question_id", name="uq_answer_per_question"),
    )

    # ---------------------------------------------------- attempt_topic_results
    op.create_table(
        "attempt_topic_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("attempt_id", sa.BigInteger(), nullable=False),
        sa.Column("topic_id", sa.BigInteger(), nullable=False),
        sa.Column("questions_total", sa.SmallInteger(), nullable=False),
        sa.Column("questions_correct", sa.SmallInteger(), nullable=False),
        sa.Column("marks_total", sa.Numeric(6, 2), nullable=False),
        sa.Column("marks_obtained", sa.Numeric(6, 2), nullable=False),
        sa.Column("accuracy", sa.Numeric(5, 4), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_attempt_topic_results"),
        sa.ForeignKeyConstraint(["attempt_id"], ["assessment_attempts.id"], name="fk_attempt_topic_results_attempt_id_assessment_attempts", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name="fk_attempt_topic_results_topic_id_topics", ondelete="CASCADE"),
        sa.UniqueConstraint("attempt_id", "topic_id", name="uq_attempt_topic"),
    )

    # -------------------------------------------------- student_skill_profiles
    op.create_table(
        "student_skill_profiles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("demonstrated_level", E("student_level"), nullable=True),
        sa.Column("recommended_level", E("student_level"), nullable=True),
        sa.Column("overall_accuracy", sa.Numeric(5, 4), nullable=True),
        sa.Column("evidence_count", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_student_skill_profiles"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_student_skill_profiles_user_id_users", ondelete="CASCADE"),
    )
    op.create_index(
        "uq_skill_profiles_one_current", "student_skill_profiles", ["user_id"], unique=True,
        postgresql_where=sa.text("is_current"),
    )

    # --------------------------------------------- student_skill_profile_topics
    op.create_table(
        "student_skill_profile_topics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("skill_profile_id", sa.BigInteger(), nullable=False),
        sa.Column("topic_id", sa.BigInteger(), nullable=False),
        sa.Column("accuracy", sa.Numeric(5, 4), nullable=True),
        sa.Column("previous_accuracy", sa.Numeric(5, 4), nullable=True),
        sa.Column("evidence_count", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("target_difficulty", E("difficulty"), nullable=True),
        sa.Column("classification", E("skill_topic_classification"), server_default="INSUFFICIENT_DATA", nullable=False),
        sa.Column("trend", E("skill_trend"), server_default="STABLE", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_student_skill_profile_topics"),
        sa.ForeignKeyConstraint(["skill_profile_id"], ["student_skill_profiles.id"], name="fk_skill_topics_profile", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name="fk_student_skill_profile_topics_topic_id_topics", ondelete="CASCADE"),
        sa.UniqueConstraint("skill_profile_id", "topic_id", name="uq_profile_topic"),
        sa.CheckConstraint("accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 1)", name="ck_student_skill_profile_topics_accuracy_range"),
    )

    # -------------------------------------------------------- recommendations
    op.create_table(
        "recommendations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("skill_profile_id", sa.BigInteger(), nullable=True),
        sa.Column("topic_id", sa.BigInteger(), nullable=False),
        sa.Column("section_id", sa.BigInteger(), nullable=True),
        sa.Column("item_id", sa.BigInteger(), nullable=True),
        sa.Column("kind", E("recommendation_kind"), nullable=False),
        sa.Column("status", E("recommendation_status"), server_default="ACTIVE", nullable=False),
        sa.Column("score", sa.Numeric(5, 4), nullable=False),
        sa.Column("weak_topic_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("difficulty_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("prerequisite_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("target_difficulty", E("difficulty"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_recommendations"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_recommendations_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_profile_id"], ["student_skill_profiles.id"], name="fk_recommendations_skill_profile_id_student_skill_profiles", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name="fk_recommendations_topic_id_topics", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["learning_sections.id"], name="fk_recommendations_section_id_learning_sections", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["learning_items.id"], name="fk_recommendations_item_id_learning_items", ondelete="CASCADE"),
        sa.CheckConstraint("item_id IS NOT NULL OR section_id IS NOT NULL", name="ck_recommendations_target_present"),
        sa.CheckConstraint(
            "score >= 0 AND score <= 1 AND weak_topic_score >= 0 AND weak_topic_score <= 1 "
            "AND difficulty_score >= 0 AND difficulty_score <= 1 "
            "AND prerequisite_score >= 0 AND prerequisite_score <= 1",
            name="ck_recommendations_score_range",
        ),
    )
    op.create_index("ix_recommendations_user_status_score", "recommendations", ["user_id", "status", sa.text("score DESC")])
    op.create_index(
        "uq_recommendations_active_per_item", "recommendations", ["user_id", "item_id"], unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND item_id IS NOT NULL"),
    )

    # --------------------------------------------------------- section_unlocks
    op.create_table(
        "section_unlocks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("section_id", sa.BigInteger(), nullable=False),
        sa.Column("status", E("unlock_status"), server_default="LOCKED", nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unlocked_by_attempt_id", sa.BigInteger(), nullable=True),
        sa.Column("completion_ratio", sa.Numeric(5, 4), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_section_unlocks"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_section_unlocks_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["learning_sections.id"], name="fk_section_unlocks_section_id_learning_sections", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unlocked_by_attempt_id"], ["assessment_attempts.id"], name="fk_section_unlocks_unlocked_by_attempt_id_assessment_attempts", ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "section_id", name="uq_section_unlock"),
    )
    op.create_index("ix_section_unlocks_user_status", "section_unlocks", ["user_id", "status"])


def downgrade() -> None:
    for table in (
        "section_unlocks", "recommendations", "student_skill_profile_topics",
        "student_skill_profiles", "attempt_topic_results", "assessment_answers",
        "assessment_attempts", "student_progress", "roadmap_enrollments",
        "assessment_options", "assessment_questions", "assessments",
        "section_items", "learning_items", "learning_sections",
        "student_profiles", "topics", "users",
    ):
        op.drop_table(table)
    bind = op.get_bind()
    for name in ENUMS:
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)