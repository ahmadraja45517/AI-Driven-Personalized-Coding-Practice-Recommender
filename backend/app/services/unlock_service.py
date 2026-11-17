from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Assessment, AssessmentAttempt, LearningSection, SectionItem,
    SectionUnlock, StudentProgress,
)
from app.models.enums import AssessmentKind, AttemptStatus, UnlockStatus


def evaluate_section(db: Session, user_id: int, section: LearningSection) -> None:
    """Re-evaluate completion for `section`. If both gates pass and it wasn't COMPLETED
    yet, mark it COMPLETED and unlock the next section (if any). Idempotent."""
    unlock = db.execute(
        select(SectionUnlock).where(
            SectionUnlock.user_id == user_id,
            SectionUnlock.section_id == section.id,
        )
    ).scalar_one_or_none()
    if unlock is None or unlock.status in (UnlockStatus.LOCKED, UnlockStatus.COMPLETED):
        return

    required_items = db.execute(
        select(SectionItem.item_id).where(
            SectionItem.section_id == section.id,
            SectionItem.is_required.is_(True),
        )
    ).scalars().all()
    total_required = len(required_items)
    if total_required == 0:
        return

    completed = db.execute(
        select(func.count()).select_from(StudentProgress).where(
            StudentProgress.user_id == user_id,
            StudentProgress.item_id.in_(required_items),
            StudentProgress.is_completed.is_(True),
        )
    ).scalar() or 0

    required_threshold = math.ceil(float(section.required_completion_ratio) * total_required)
    passes_completion = completed >= required_threshold

    best_attempt = db.execute(
        select(AssessmentAttempt)
        .join(Assessment, Assessment.id == AssessmentAttempt.assessment_id)
        .where(
            AssessmentAttempt.user_id == user_id,
            Assessment.section_id == section.id,
            Assessment.kind == AssessmentKind.SECTION_END,
            AssessmentAttempt.status == AttemptStatus.SUBMITTED,
        )
        .order_by(AssessmentAttempt.percentage.desc())
        .limit(1)
    ).scalar_one_or_none()
    passes_assessment = best_attempt is not None and bool(best_attempt.passed)

    if not (passes_completion and passes_assessment):
        return

    unlock.status = UnlockStatus.COMPLETED
    unlock.completed_at = datetime.now(timezone.utc)
    unlock.unlocked_by_attempt_id = best_attempt.id if best_attempt else None
    unlock.completion_ratio = completed / total_required

    next_section = db.execute(
        select(LearningSection).where(
            LearningSection.target_level == section.target_level,
            LearningSection.order_index == section.order_index + 1,
            LearningSection.content_status == "PUBLISHED",
        )
    ).scalar_one_or_none()
    if next_section is not None:
        next_unlock = db.execute(
            select(SectionUnlock).where(
                SectionUnlock.user_id == user_id,
                SectionUnlock.section_id == next_section.id,
            )
        ).scalar_one_or_none()
        if next_unlock is not None and next_unlock.status == UnlockStatus.LOCKED:
            next_unlock.status = UnlockStatus.UNLOCKED
            next_unlock.unlocked_at = datetime.now(timezone.utc)
    db.flush()


def evaluate_section_by_id(db: Session, user_id: int, section_id: int) -> None:
    section = db.get(LearningSection, section_id)
    if section is not None:
        evaluate_section(db, user_id, section)