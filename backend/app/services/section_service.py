from __future__ import annotations

import math

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Assessment, AssessmentAttempt, LearningItem, LearningSection,
    RoadmapEnrollment, SectionItem, SectionUnlock, StudentProgress,
)
from app.models.enums import (
    AssessmentKind, AttemptStatus, EnrollmentStatus, StudentLevel, UnlockStatus,
)
from app.schemas.sections import (
    ItemForSection, SectionDetailResponse, SectionListResponse,
    SectionProgress, SectionSummary,
)


def _active_enrollment(db: Session, user_id: int) -> RoadmapEnrollment | None:
    return db.execute(
        select(RoadmapEnrollment).where(
            RoadmapEnrollment.user_id == user_id,
            RoadmapEnrollment.status == EnrollmentStatus.ACTIVE,
        )
    ).scalar_one_or_none()


def _progress_for_section(db: Session, user_id: int, section: LearningSection) -> SectionProgress:
    required_ids = db.execute(
        select(SectionItem.item_id).where(
            SectionItem.section_id == section.id, SectionItem.is_required.is_(True),
        )
    ).scalars().all()
    total = len(required_ids)

    if total == 0:
        return SectionProgress(
            items_total=0, items_completed=0, items_required_threshold=0,
            completion_ratio=0.0, passes_completion=False,
            best_assessment_pct=None,
            assessment_pass_threshold_pct=float(section.required_assessment_ratio) * 100,
            passes_assessment=False, requirements_met=False,
        )

    completed = db.execute(
        select(func.count()).select_from(StudentProgress).where(
            StudentProgress.user_id == user_id,
            StudentProgress.item_id.in_(required_ids),
            StudentProgress.is_completed.is_(True),
        )
    ).scalar() or 0

    threshold = math.ceil(float(section.required_completion_ratio) * total)
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

    best_pct = float(best_attempt.percentage) if best_attempt and best_attempt.percentage is not None else None
    pass_threshold = float(section.required_assessment_ratio) * 100
    passes_assessment = best_pct is not None and best_pct >= pass_threshold

    return SectionProgress(
        items_total=total,
        items_completed=completed,
        items_required_threshold=threshold,
        completion_ratio=round(completed / total, 4),
        passes_completion=completed >= threshold,
        best_assessment_pct=round(best_pct, 2) if best_pct is not None else None,
        assessment_pass_threshold_pct=round(pass_threshold, 2),
        passes_assessment=passes_assessment,
        requirements_met=(completed >= threshold) and passes_assessment,
    )


def list_sections(db: Session, user_id: int) -> SectionListResponse:
    sections = db.execute(
        select(LearningSection)
        .where(
            LearningSection.target_level == StudentLevel.BEGINNER,
            LearningSection.content_status == "PUBLISHED",
        )
        .order_by(LearningSection.order_index)
    ).scalars().all()

    enrollment = _active_enrollment(db, user_id)
    if enrollment is None:
        return SectionListResponse(enrolled=False, sections=[
            SectionSummary(
                id=s.id, slug=s.slug, title=s.title, description=s.description,
                order_index=s.order_index, content_status=s.content_status.value,
                status="NOT_ENROLLED", progress=None,
            ) for s in sections
        ])

    unlocks = {
        u.section_id: u for u in db.execute(
            select(SectionUnlock).where(SectionUnlock.user_id == user_id)
        ).scalars().all()
    }

    summaries: list[SectionSummary] = []
    for s in sections:
        unlock = unlocks.get(s.id)
        status = unlock.status.value if unlock else "LOCKED"
        progress = _progress_for_section(db, user_id, s) if status != "LOCKED" else None
        summaries.append(SectionSummary(
            id=s.id, slug=s.slug, title=s.title, description=s.description,
            order_index=s.order_index, content_status=s.content_status.value,
            status=status, progress=progress,
        ))
    return SectionListResponse(enrolled=True, sections=summaries)


def get_section_detail(db: Session, user_id: int, section_id: int) -> SectionDetailResponse:
    section = db.get(LearningSection, section_id)
    if section is None or section.target_level != StudentLevel.BEGINNER or section.content_status != "PUBLISHED":
        raise PermissionError("Section not available")

    enrollment = _active_enrollment(db, user_id)
    if enrollment is None:
        raise PermissionError("You must be enrolled in the beginner roadmap")

    unlock = db.execute(
        select(SectionUnlock).where(
            SectionUnlock.user_id == user_id, SectionUnlock.section_id == section_id,
        )
    ).scalar_one_or_none()
    if unlock is None or unlock.status == UnlockStatus.LOCKED:
        raise PermissionError("This section is locked")

    rows = db.execute(
        select(LearningItem, SectionItem.order_index, StudentProgress)
        .join(SectionItem, SectionItem.item_id == LearningItem.id)
        .outerjoin(
            StudentProgress,
            (StudentProgress.item_id == LearningItem.id) & (StudentProgress.user_id == user_id),
        )
        .where(SectionItem.section_id == section_id)
        .order_by(SectionItem.order_index)
    ).all()

    items: list[ItemForSection] = []
    for item, _order, progress in rows:
        items.append(ItemForSection(
            id=item.id,
            title=item.title,
            kind=item.kind,
            source=item.source,
            difficulty=item.difficulty,
            content_md=item.content_md,
            external_url=item.external_url,
            estimated_minutes=item.estimated_minutes,
            is_completed=bool(progress and progress.is_completed),
            completed_at=progress.completed_at.isoformat() if progress and progress.completed_at else None,
        ))
    return SectionDetailResponse(
        id=section.id, slug=section.slug, title=section.title,
        description=section.description, status=unlock.status.value, items=items,
    )