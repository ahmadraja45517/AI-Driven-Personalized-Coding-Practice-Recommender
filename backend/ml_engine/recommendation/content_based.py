"""Candidate loading and filtering for the recommendation engine.

Queries the DB but does no scoring. hybrid.py applies rule_based.py
formulas to these candidates and produces Recommendation rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    LearningItem, LearningSection, SectionItem, SectionUnlock,
    SkillProfile, SkillProfileTopic, StudentProgress, Topic,
)
from app.models.enums import (
    Difficulty, SectionContentStatus, SkillTopicClassification,
    StudentLevel, UnlockStatus,
)
from ml_engine.recommendation.rule_based import (
    classify_topic, difficulty_value, target_difficulty_for,
)


# --- Data carriers ----------------------------------------------------------

@dataclass(frozen=True)
class TopicSnapshot:
    topic_id: int
    code: str
    name: str
    accuracy: float
    classification: SkillTopicClassification
    target_difficulty: Difficulty


@dataclass(frozen=True)
class ItemCandidate:
    item_id: int
    item_title: str
    item_difficulty: Optional[Difficulty]
    section_id: int
    section_title: str
    section_order: int
    section_unlocked: bool
    item_completed: bool
    topic: TopicSnapshot
    prerequisite_p: float


@dataclass(frozen=True)
class SectionHintCandidate:
    section_id: int
    section_title: str
    section_order: int
    topic: TopicSnapshot
    prerequisite_p: float
    prerequisite_section_title: Optional[str]
    average_item_difficulty: Optional[float]


# --- Loaders ----------------------------------------------------------------

def load_topic_snapshots(db: Session, skill_profile: SkillProfile) -> dict[int, TopicSnapshot]:
    """Return {topic_id: TopicSnapshot} for every topic with usable accuracy data.

    Topics classified INSUFFICIENT_DATA are omitted so callers cannot
    accidentally recommend for un-assessed topics.
    """
    rows = db.execute(
        select(SkillProfileTopic, Topic)
        .join(Topic, Topic.id == SkillProfileTopic.topic_id)
        .where(SkillProfileTopic.skill_profile_id == skill_profile.id)
        .where(Topic.is_active.is_(True))
    ).all()
    out: dict[int, TopicSnapshot] = {}
    for spt, topic in rows:
        if spt.accuracy is None:
            continue
        if spt.classification == SkillTopicClassification.INSUFFICIENT_DATA:
            continue
        acc = float(spt.accuracy)
        out[topic.id] = TopicSnapshot(
            topic_id=topic.id,
            code=topic.code,
            name=topic.name,
            accuracy=acc,
            classification=spt.classification,
            target_difficulty=target_difficulty_for(acc),
        )
    return out


def load_unlocked_map(db: Session, user_id: int) -> dict[int, UnlockStatus]:
    rows = db.execute(
        select(SectionUnlock).where(SectionUnlock.user_id == user_id)
    ).scalars().all()
    return {r.section_id: r.status for r in rows}


def load_completed_item_ids(db: Session, user_id: int) -> set[int]:
    rows = db.execute(
        select(StudentProgress.item_id).where(
            StudentProgress.user_id == user_id,
            StudentProgress.is_completed.is_(True),
        )
    ).scalars().all()
    return set(rows)


def load_beginner_sections(db: Session) -> list[LearningSection]:
    return list(db.execute(
        select(LearningSection)
        .where(LearningSection.target_level == StudentLevel.BEGINNER)
        .where(LearningSection.content_status == SectionContentStatus.PUBLISHED)
        .order_by(LearningSection.order_index)
    ).scalars().all())


def compute_section_p_map(
    sections: list[LearningSection], unlocks: dict[int, UnlockStatus],
) -> dict[int, float]:
    """P for each section per the agreed formula.

    - Unlocked or COMPLETED section -> P = 1.0
    - First section (order_index <= 1) -> P = 1.0
    - Otherwise -> P = (completed sections with order_index < k) / k
    """
    result: dict[int, float] = {}
    completed_before = 0
    for section in sorted(sections, key=lambda s: s.order_index):
        k = section.order_index
        status = unlocks.get(section.id)
        if status in (UnlockStatus.UNLOCKED, UnlockStatus.COMPLETED):
            result[section.id] = 1.0
        elif k <= 1:
            result[section.id] = 1.0
        else:
            result[section.id] = min(1.0, completed_before / k)
        if status == UnlockStatus.COMPLETED:
            completed_before += 1
    return result


# --- Candidate builders -----------------------------------------------------

def build_item_candidates(
    db: Session,
    topic_snapshots: dict[int, TopicSnapshot],
    unlocks: dict[int, UnlockStatus],
    completed_ids: set[int],
    sections: list[LearningSection],
    p_map: dict[int, float],
) -> list[ItemCandidate]:
    """Load every active beginner item whose topic has usable evidence.

    Items in topics with INSUFFICIENT_DATA are silently skipped — they
    cannot be recommended honestly.
    """
    if not sections:
        return []
    section_ids = [s.id for s in sections]

    rows = db.execute(
        select(LearningItem, SectionItem.section_id, LearningSection)
        .join(SectionItem, SectionItem.item_id == LearningItem.id)
        .join(LearningSection, LearningSection.id == SectionItem.section_id)
        .where(SectionItem.section_id.in_(section_ids))
        .where(LearningItem.is_active.is_(True))
        .where(LearningItem.topic_id.in_(list(topic_snapshots.keys())))
    ).all()

    out: list[ItemCandidate] = []
    for item, section_id, section in rows:
        topic = topic_snapshots.get(item.topic_id)
        if topic is None:
            continue
        status = unlocks.get(section_id)
        out.append(ItemCandidate(
            item_id=item.id,
            item_title=item.title,
            item_difficulty=item.difficulty,
            section_id=section.id,
            section_title=section.title,
            section_order=section.order_index,
            section_unlocked=status in (UnlockStatus.UNLOCKED, UnlockStatus.COMPLETED),
            item_completed=item.id in completed_ids,
            topic=topic,
            prerequisite_p=p_map.get(section.id, 0.0),
        ))
    return out


def build_section_hint_candidates(
    db: Session,
    topic_snapshots: dict[int, TopicSnapshot],
    unlocks: dict[int, UnlockStatus],
    sections: list[LearningSection],
    p_map: dict[int, float],
) -> list[SectionHintCandidate]:
    """One hint per locked section whose topic is WEAK or NEEDS_REVISION."""
    section_by_order = {s.order_index: s for s in sections}
    # Preload average difficulty per section in one query
    diff_rows = db.execute(
        select(LearningItem.section_id, LearningItem.difficulty)
        .join(SectionItem, SectionItem.item_id == LearningItem.id)
        .where(SectionItem.section_id.in_([s.id for s in sections]))
        .where(LearningItem.is_active.is_(True))
        .where(LearningItem.difficulty.isnot(None))
    ).all() if False else []  # placeholder to avoid unused var warning

    # Simpler: query per-section averages in one shot
    from sqlalchemy import func
    avg_rows = db.execute(
        select(SectionItem.section_id, LearningItem.difficulty)
        .join(LearningItem, LearningItem.id == SectionItem.item_id)
        .where(SectionItem.section_id.in_([s.id for s in sections]))
        .where(LearningItem.is_active.is_(True))
        .where(LearningItem.difficulty.isnot(None))
    ).all()

    per_section_values: dict[int, list[int]] = {}
    for section_id, diff in avg_rows:
        per_section_values.setdefault(section_id, []).append(difficulty_value(diff))

    out: list[SectionHintCandidate] = []
    for section in sections:
        if unlocks.get(section.id) in (UnlockStatus.UNLOCKED, UnlockStatus.COMPLETED):
            continue
        if section.topic_id is None:
            continue
        topic = topic_snapshots.get(section.topic_id)
        if topic is None:
            continue
        if topic.classification not in (
            SkillTopicClassification.WEAK,
            SkillTopicClassification.NEEDS_REVISION,
        ):
            continue
        prev_section = section_by_order.get(section.order_index - 1)
        values = per_section_values.get(section.id, [])
        avg_diff = sum(values) / len(values) if values else None
        out.append(SectionHintCandidate(
            section_id=section.id,
            section_title=section.title,
            section_order=section.order_index,
            topic=topic,
            prerequisite_p=p_map.get(section.id, 0.0),
            prerequisite_section_title=prev_section.title if prev_section else None,
            average_item_difficulty=avg_diff,
        ))
    return out