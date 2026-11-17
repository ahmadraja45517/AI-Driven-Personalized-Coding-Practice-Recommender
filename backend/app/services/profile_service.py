from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    LearningSection, RoadmapEnrollment, SectionUnlock,
    SkillProfile, StudentProfile, User,
)
from app.models.enums import (
    EnrollmentStatus, StudentLevel, UnlockStatus,
)
from app.schemas.profile import (
    EnrollRoadmapResponse, LevelRecommendation, OnboardingRequest,
    ProfileResponse, ProfileUpdate,
)


class ProfileError(Exception):
    pass


def _ensure_profile(db: Session, user: User) -> StudentProfile:
    profile = db.execute(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    ).scalar_one_or_none()
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
        db.flush()
    return profile


def _current_skill_profile(db: Session, user_id: int) -> SkillProfile | None:
    return db.execute(
        select(SkillProfile).where(
            SkillProfile.user_id == user_id,
            SkillProfile.is_current.is_(True),
        )
    ).scalar_one_or_none()


def _build_level_recommendation(selected: StudentLevel | None, skill: SkillProfile | None) -> LevelRecommendation:
    if skill is None or skill.recommended_level is None or selected is None:
        return LevelRecommendation(show=False)
    if skill.recommended_level == selected:
        return LevelRecommendation(
            show=False,
            recommended_level=skill.recommended_level,
            demonstrated_level=skill.demonstrated_level,
        )
    message = (
        f"Your assessment results suggest that the {skill.recommended_level.value.title()} "
        "learning path may be more suitable for your current skill level. "
        "This is a recommendation only — your selected level remains unchanged."
    )
    return LevelRecommendation(
        show=True,
        recommended_level=skill.recommended_level,
        demonstrated_level=skill.demonstrated_level,
        message=message,
    )


def _get_active_enrollment(db: Session, user_id: int) -> RoadmapEnrollment | None:
    return db.execute(
        select(RoadmapEnrollment).where(
            RoadmapEnrollment.user_id == user_id,
            RoadmapEnrollment.status == EnrollmentStatus.ACTIVE,
        )
    ).scalar_one_or_none()


def _bootstrap_beginner_roadmap(db: Session, user_id: int) -> RoadmapEnrollment:
    sections = db.execute(
        select(LearningSection)
        .where(LearningSection.target_level == StudentLevel.BEGINNER)
        .order_by(LearningSection.order_index)
    ).scalars().all()
    if not sections:
        raise ProfileError("No beginner roadmap sections configured")

    enrollment = RoadmapEnrollment(
        user_id=user_id, roadmap_level=StudentLevel.BEGINNER, status=EnrollmentStatus.ACTIVE,
    )
    db.add(enrollment)
    db.flush()

    now = datetime.now(timezone.utc)
    for idx, section in enumerate(sections):
        is_first = idx == 0
        db.add(SectionUnlock(
            user_id=user_id,
            section_id=section.id,
            status=UnlockStatus.UNLOCKED if is_first else UnlockStatus.LOCKED,
            unlocked_at=now if is_first else None,
        ))
    db.flush()
    return enrollment


def complete_onboarding(db: Session, user: User, req: OnboardingRequest) -> ProfileResponse:
    profile = _ensure_profile(db, user)
    profile.preferred_language = req.preferred_language
    profile.selected_level = req.selected_level
    profile.onboarding_completed_at = datetime.now(timezone.utc)

    if req.selected_level == StudentLevel.BEGINNER and _get_active_enrollment(db, user.id) is None:
        _bootstrap_beginner_roadmap(db, user.id)
    db.commit()
    db.refresh(profile)
    return build_profile_response(db, user, profile)


def update_profile(db: Session, user: User, req: ProfileUpdate) -> ProfileResponse:
    profile = _ensure_profile(db, user)
    if req.preferred_language is not None:
        profile.preferred_language = req.preferred_language
    if req.selected_level is not None:
        profile.selected_level = req.selected_level
        if req.selected_level == StudentLevel.BEGINNER and _get_active_enrollment(db, user.id) is None:
            _bootstrap_beginner_roadmap(db, user.id)
    db.commit()
    db.refresh(profile)
    return build_profile_response(db, user, profile)


def enroll_in_roadmap(db: Session, user: User) -> EnrollRoadmapResponse:
    existing = _get_active_enrollment(db, user.id)
    if existing is not None:
        return EnrollRoadmapResponse(
            enrollment_id=existing.id,
            roadmap_level=existing.roadmap_level,
            status=existing.status.value,
        )
    enrollment = _bootstrap_beginner_roadmap(db, user.id)
    db.commit()
    return EnrollRoadmapResponse(
        enrollment_id=enrollment.id,
        roadmap_level=enrollment.roadmap_level,
        status=enrollment.status.value,
    )


def build_profile_response(db: Session, user: User, profile: StudentProfile) -> ProfileResponse:
    skill = _current_skill_profile(db, user.id)
    rec = _build_level_recommendation(profile.selected_level, skill)
    return ProfileResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        course=user.course,
        academic_year=user.academic_year,
        preferred_language=profile.preferred_language,
        selected_level=profile.selected_level,
        onboarding_completed_at=profile.onboarding_completed_at,
        demonstrated_level=skill.demonstrated_level if skill else None,
        recommended_level=skill.recommended_level if skill else None,
        level_recommendation=rec,
    )


def get_profile(db: Session, user: User) -> ProfileResponse:
    profile = _ensure_profile(db, user)
    db.commit()
    return build_profile_response(db, user, profile)