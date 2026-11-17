from __future__ import annotations
from app.models import Assessment  # in addition to the existing imports
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Assessment, AssessmentAttempt, AttemptTopicResult, SkillProfile,
    SkillProfileTopic, StudentProfile, Topic,
)
from app.models.enums import (
    AssessmentKind, Difficulty, SkillTopicClassification,
    SkillTrend, StudentLevel,
)
from app.schemas.skill import SkillProfileResponse, SkillTopicEntry


def _difficulty_from_accuracy(acc: float) -> Difficulty:
    if acc < 0.40:
        return Difficulty.EASY
    if acc < 0.70:
        return Difficulty.MEDIUM
    return Difficulty.HARD


def _classification_from_accuracy(acc: float) -> SkillTopicClassification:
    if acc >= 0.70:
        return SkillTopicClassification.STRONG
    if acc < 0.40:
        return SkillTopicClassification.WEAK
    return SkillTopicClassification.NEEDS_REVISION


def _level_from_accuracy(acc: float) -> StudentLevel:
    if acc >= 0.70:
        return StudentLevel.ADVANCED
    if acc >= 0.40:
        return StudentLevel.INTERMEDIATE
    return StudentLevel.BEGINNER


def recompute_skill_profile_from_attempt(
    db: Session, user_id: int, attempt: AssessmentAttempt,
) -> SkillProfile:
    """Rebuild the current skill profile from the given attempt.

    - DIAGNOSTIC: full replacement (all topics reflect this diagnostic).
    - SECTION_END: partial merge. Topics covered by this attempt get new
      data; other topics carry over from the previous snapshot so Beginner
      students accumulate evidence across section-ends without losing it.
    """
    assessment = db.get(Assessment, attempt.assessment_id)

    previous = db.execute(
        select(SkillProfile).where(
            SkillProfile.user_id == user_id,
            SkillProfile.is_current.is_(True),
        )
    ).scalar_one_or_none()
    prev_topic_data: dict[int, dict] = {}
    if previous is not None:
        for t in previous.topics:
            prev_topic_data[t.topic_id] = {
                "accuracy": float(t.accuracy) if t.accuracy is not None else None,
                "evidence_count": t.evidence_count,
                "target_difficulty": t.target_difficulty,
                "classification": t.classification,
                "trend": t.trend,
            }
        previous.is_current = False
        db.flush()

    if assessment is not None and assessment.kind == AssessmentKind.DIAGNOSTIC:
        prev_topic_data = {}  # full replacement

    topic_rows = db.execute(
        select(AttemptTopicResult).where(AttemptTopicResult.attempt_id == attempt.id)
    ).scalars().all()
    new_acc = {r.topic_id: float(r.accuracy) for r in topic_rows}
    new_q = {r.topic_id: r.questions_total for r in topic_rows}

    all_topics = db.execute(select(Topic).where(Topic.is_active.is_(True))).scalars().all()

    merged: dict[int, dict] = {}
    for topic in all_topics:
        if topic.id in new_acc:
            prev = prev_topic_data.get(topic.id, {}).get("accuracy")
            merged[topic.id] = {
                "accuracy": new_acc[topic.id],
                "previous_accuracy": prev,
                "evidence_count": new_q.get(topic.id, 0),
            }
        elif topic.id in prev_topic_data and prev_topic_data[topic.id]["accuracy"] is not None:
            pd = prev_topic_data[topic.id]
            merged[topic.id] = {
                "accuracy": pd["accuracy"],
                "previous_accuracy": pd["accuracy"],
                "evidence_count": pd["evidence_count"],
            }

    overall: Optional[float] = None
    total_evidence = 0
    if merged:
        total_weight = sum(td["evidence_count"] for td in merged.values())
        if total_weight > 0:
            overall = sum(td["accuracy"] * td["evidence_count"] for td in merged.values()) / total_weight
            total_evidence = total_weight
        else:
            overall = sum(td["accuracy"] for td in merged.values()) / len(merged)

    profile = SkillProfile(
        user_id=user_id,
        is_current=True,
        computed_at=datetime.now(timezone.utc),
        overall_accuracy=round(overall, 4) if overall is not None else None,
        evidence_count=total_evidence,
    )
    if overall is not None:
        profile.demonstrated_level = _level_from_accuracy(overall)
        profile.recommended_level = profile.demonstrated_level
    db.add(profile)
    db.flush()

    for topic in all_topics:
        if topic.id in merged:
            td = merged[topic.id]
            acc = td["accuracy"]
            prev = td["previous_accuracy"]
            if prev is None:
                trend = SkillTrend.STABLE
            elif acc > prev + 0.05:
                trend = SkillTrend.IMPROVING
            elif acc < prev - 0.05:
                trend = SkillTrend.DECLINING
            else:
                trend = SkillTrend.STABLE
            db.add(SkillProfileTopic(
                skill_profile_id=profile.id,
                topic_id=topic.id,
                accuracy=round(acc, 4),
                previous_accuracy=round(prev, 4) if prev is not None else None,
                evidence_count=td["evidence_count"],
                target_difficulty=_difficulty_from_accuracy(acc),
                classification=_classification_from_accuracy(acc),
                trend=trend,
            ))
        else:
            db.add(SkillProfileTopic(
                skill_profile_id=profile.id,
                topic_id=topic.id,
                accuracy=None,
                previous_accuracy=None,
                evidence_count=0,
                target_difficulty=None,
                classification=SkillTopicClassification.INSUFFICIENT_DATA,
                trend=SkillTrend.STABLE,
            ))
    db.flush()
    return profile


def get_current_skill_profile(db: Session, user_id: int) -> SkillProfileResponse | None:
    profile = db.execute(
        select(SkillProfile).where(
            SkillProfile.user_id == user_id, SkillProfile.is_current.is_(True),
        )
    ).scalar_one_or_none()
    if profile is None:
        return None

    topics = db.execute(
        select(SkillProfileTopic, Topic.code)
        .join(Topic, Topic.id == SkillProfileTopic.topic_id)
        .where(SkillProfileTopic.skill_profile_id == profile.id)
    ).all()

    return SkillProfileResponse(
        profile_id=profile.id,
        computed_at=profile.computed_at,
        demonstrated_level=profile.demonstrated_level,
        recommended_level=profile.recommended_level,
        overall_accuracy=float(profile.overall_accuracy) if profile.overall_accuracy is not None else None,
        evidence_count=profile.evidence_count,
        topics=[
            SkillTopicEntry(
                topic=code,
                accuracy=float(t.accuracy) if t.accuracy is not None else None,
                evidence_count=t.evidence_count,
                target_difficulty=t.target_difficulty,
                classification=t.classification,
                trend=t.trend,
            ) for t, code in topics
        ],
    )