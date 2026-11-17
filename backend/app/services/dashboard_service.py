from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Assessment, AssessmentAttempt, LearningSection, RoadmapEnrollment,
    SectionItem, SectionUnlock, StudentProfile, StudentProgress, User,
)
from app.models.enums import (
    AssessmentKind, AttemptStatus, EnrollmentStatus, StudentLevel, UnlockStatus,
)
from app.schemas.assessments import AssessmentSummary
from app.schemas.dashboard import DashboardResponse, DiagnosticHistory, ProgressSummary
from app.schemas.sections import SectionSummary
from app.services.assessment_service import _attempt_stats
from app.services.profile_service import _build_level_recommendation
from app.services.recommendation_service import list_recommendations
from app.services.section_service import list_sections
from app.services.skill_service import get_current_skill_profile


def build_dashboard(db: Session, user: User) -> DashboardResponse:
    profile = db.execute(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    ).scalar_one_or_none()

    sections_resp = list_sections(db, user.id)
    skill = get_current_skill_profile(db, user.id)

    all_items = db.execute(
        select(func.count()).select_from(SectionItem).join(
            LearningSection, LearningSection.id == SectionItem.section_id,
        ).where(LearningSection.target_level == StudentLevel.BEGINNER)
    ).scalar() or 0
    completed_items = db.execute(
        select(func.count()).select_from(StudentProgress).where(
            StudentProgress.user_id == user.id,
            StudentProgress.is_completed.is_(True),
        )
    ).scalar() or 0

    unlocked = sum(1 for s in sections_resp.sections if s.status in ("UNLOCKED", "COMPLETED"))
    completed = sum(1 for s in sections_resp.sections if s.status == "COMPLETED")
    current = next((s.slug for s in sections_resp.sections if s.status == "UNLOCKED"), None)

    diagnostic_history = None
    diagnostic: Assessment | None = None
    if profile is not None and profile.selected_level in (StudentLevel.INTERMEDIATE, StudentLevel.ADVANCED):
        diagnostic = db.execute(
            select(Assessment).where(
                Assessment.kind == AssessmentKind.DIAGNOSTIC,
                Assessment.target_level == profile.selected_level,
                Assessment.is_active.is_(True),
            )
        ).scalar_one_or_none()
    if diagnostic is not None:
        count, best, latest, _ = _attempt_stats(db, user.id, diagnostic.id)
        first_pct = None
        if count:
            first = db.execute(
                select(AssessmentAttempt.percentage).where(
                    AssessmentAttempt.user_id == user.id,
                    AssessmentAttempt.assessment_id == diagnostic.id,
                    AssessmentAttempt.status == AttemptStatus.SUBMITTED,
                ).order_by(AssessmentAttempt.submitted_at.asc()).limit(1)
            ).scalar_one_or_none()
            first_pct = float(first) if first is not None else None
        diagnostic_history = DiagnosticHistory(
            first_pct=first_pct, latest_pct=latest, best_pct=best, attempts_count=count,
        )

    section_assessments: list[AssessmentSummary] = []
    for a in db.execute(
        select(Assessment).where(
            Assessment.kind == AssessmentKind.SECTION_END,
            Assessment.is_active.is_(True),
        )
    ).scalars().all():
        cnt, best, latest, passed = _attempt_stats(db, user.id, a.id)
        section_assessments.append(AssessmentSummary(
            id=a.id, kind=a.kind, title=a.title, description=a.description,
            target_level=a.target_level, section_id=a.section_id,
            total_marks=a.total_marks, pass_ratio=float(a.pass_ratio),
            duration_minutes=a.duration_minutes,
            attempts_count=cnt, best_pct=best, latest_pct=latest, passed=passed,
        ))

    recs = list_recommendations(db, user.id)

    return DashboardResponse(
        full_name=user.full_name,
        preferred_language=profile.preferred_language if profile else None,
        selected_level=profile.selected_level if profile else None,
        demonstrated_level=skill.demonstrated_level if skill else None,
        recommended_level=skill.recommended_level if skill else None,
        level_recommendation=_build_level_recommendation(
            profile.selected_level if profile else None,
            db.execute(select(StudentProfile)).scalar_one_or_none() and None,
        ) if False else _build_level_recommendation(
            profile.selected_level if profile else None,
            _skill_model(db, user.id),
        ),
        progress=ProgressSummary(
            total_items=all_items,
            completed_items=completed_items,
            completion_ratio=round(completed_items / all_items, 4) if all_items else 0.0,
            current_section=current,
            unlocked_sections=unlocked,
            completed_sections=completed,
        ),
        sections=sections_resp.sections,
        diagnostic_history=diagnostic_history,
        section_assessments=section_assessments,
        skill_profile=skill,
        recommendations=recs.items,
    )


def _skill_model(db: Session, user_id: int):
    from app.models import SkillProfile
    return db.execute(
        select(SkillProfile).where(
            SkillProfile.user_id == user_id, SkillProfile.is_current.is_(True),
        )
    ).scalar_one_or_none()