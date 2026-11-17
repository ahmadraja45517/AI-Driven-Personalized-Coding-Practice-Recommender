"""Hybrid rule-based + content-based recommendation engine.

Replaces the Deliverable B stub. Pure Python — no external ML libs,
no schema changes, no migrations. Writes Recommendation rows to the
session that the caller commits.

Formula:
    R = 0.40·W + 0.35·D + 0.25·P

Kinds:
    ACTIONABLE       uncompleted item, topic WEAK/NEEDS_REVISION, section unlocked
    LOCKED_PREVIEW   item in a locked section OR a section-level path hint
    REVISION         already-completed item, any classification

Generating twice is idempotent: previous ACTIVE rows are marked EXPIRED
and new rows are inserted within the caller's transaction.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Recommendation, SkillProfile
from app.models.enums import (
    Difficulty, RecommendationKind, RecommendationStatus,
    SkillTopicClassification,
)
from ml_engine.recommendation.content_based import (
    ItemCandidate, SectionHintCandidate,
    build_item_candidates, build_section_hint_candidates,
    compute_section_p_map, load_beginner_sections, load_completed_item_ids,
    load_topic_snapshots, load_unlocked_map,
)
from ml_engine.recommendation.ranking import rank_top_n
from ml_engine.recommendation.rule_based import (
    STRONG_ACCURACY_THRESHOLD, WEAK_ACCURACY_THRESHOLD,
    difficulty_suitability, difficulty_value,
    recommendation_score, weak_topic_relevance,
)

log = logging.getLogger(__name__)

ENGINE_AVAILABLE: bool = True


# --- Configurable limits (Decision 5) ---------------------------------------

ACTIONABLE_LIMIT: int = 10
LOCKED_PREVIEW_LIMIT: int = 3
REVISION_LIMIT: int = 3


# --- Internal record used only within this module ---------------------------

@dataclass(frozen=True)
class _Scored:
    kind: RecommendationKind
    topic_id: int
    section_id: Optional[int]
    item_id: Optional[int]
    score: float
    w: float
    d: float
    p: float
    target_difficulty: Optional[Difficulty]
    reason: str


# --- Reason builders (Decision 7) -------------------------------------------

def _reason_for_item(kind: RecommendationKind, topic_name: str, accuracy: float, item_title: str) -> str:
    pct = round(accuracy * 100, 1)
    if kind == RecommendationKind.REVISION and accuracy >= STRONG_ACCURACY_THRESHOLD:
        return f"You scored {pct}% in {topic_name} — reinforce with '{item_title}'"
    if accuracy < WEAK_ACCURACY_THRESHOLD:
        return f"Your accuracy in {topic_name} is {pct}%. Try '{item_title}' to improve."
    return f"You're at {pct}% in {topic_name}. Try '{item_title}' to solidify your skills."0


def _reason_for_section_hint(topic_name: str, prerequisite_title: Optional[str]) -> str:
    if prerequisite_title:
        return f"{topic_name} needs work, but the section is locked. Complete {prerequisite_title} first."
    return f"{topic_name} needs work, but the section is locked."


# --- Score computation for a single item candidate --------------------------

def _score_item(c: ItemCandidate) -> _Scored:
    w = weak_topic_relevance(c.topic.accuracy)
    if c.item_difficulty is None:
        d = 0.5  # neutral for lessons without a difficulty tag
    else:
        d = difficulty_suitability(
            difficulty_value(c.item_difficulty),
            difficulty_value(c.topic.target_difficulty),
        )
    p = c.prerequisite_p
    score = recommendation_score(w, d, p)

    if c.item_completed:
        kind = RecommendationKind.REVISION
    elif c.section_unlocked:
        kind = RecommendationKind.ACTIONABLE
    else:
        kind = RecommendationKind.LOCKED_PREVIEW

    return _Scored(
        kind=kind,
        topic_id=c.topic.topic_id,
        section_id=c.section_id if kind == RecommendationKind.LOCKED_PREVIEW else None,
        item_id=c.item_id,
        score=score,
        w=w, d=d, p=p,
        target_difficulty=c.topic.target_difficulty,
        reason=_reason_for_item(kind, c.topic.name, c.topic.accuracy),
    )


def _score_section_hint(h: SectionHintCandidate) -> _Scored:
    w = weak_topic_relevance(h.topic.accuracy)
    if h.average_item_difficulty is None:
        d = 0.5
    else:
        d = difficulty_suitability(
            h.average_item_difficulty,
            difficulty_value(h.topic.target_difficulty),
        )
    p = h.prerequisite_p
    score = recommendation_score(w, d, p)
    return _Scored(
        kind=RecommendationKind.LOCKED_PREVIEW,
        topic_id=h.topic.topic_id,
        section_id=h.section_id,
        item_id=None,
        score=score,
        w=w, d=d, p=p,
        target_difficulty=h.topic.target_difficulty,
        reason=_reason_for_section_hint(h.topic.name, h.prerequisite_section_title),
    )


# --- Locked-preview selection: hints first, then item previews --------------

def _select_locked(
    hints: list[_Scored], previews: list[_Scored], limit: int,
) -> list[_Scored]:
    picked_hints = rank_top_n(
        hints, key_fn=lambda r: r.section_id, score_fn=lambda r: r.score, limit=limit,
    )
    remaining = limit - len(picked_hints)
    if remaining <= 0:
        return picked_hints
    picked_previews = rank_top_n(
        previews, key_fn=lambda r: r.item_id, score_fn=lambda r: r.score, limit=remaining,
    )
    return picked_hints + picked_previews


# --- Public entry point -----------------------------------------------------

def _current_skill_profile(db: Session, user_id: int) -> Optional[SkillProfile]:
    return db.execute(
        select(SkillProfile).where(
            SkillProfile.user_id == user_id,
            SkillProfile.is_current.is_(True),
        )
    ).scalar_one_or_none()


def generate_for_user(db: Session, user_id: int) -> None:
    """Regenerate ACTIVE recommendations for the given user.

    Returns silently if the user has no current skill profile or if no
    topic has usable evidence. Does NOT commit — the caller owns the
    transaction boundary.
    """
    skill = _current_skill_profile(db, user_id)
    if skill is None:
        log.debug("No current skill profile for user %s — skipping", user_id)
        return

    topic_snapshots = load_topic_snapshots(db, skill)
    if not topic_snapshots:
        log.debug("No usable topic data for user %s — skipping", user_id)
        return

    unlocks = load_unlocked_map(db, user_id)
    completed_ids = load_completed_item_ids(db, user_id)
    sections = load_beginner_sections(db)
    if not sections:
        log.warning("No beginner sections configured — cannot generate recommendations")
        return
    p_map = compute_section_p_map(sections, unlocks)

    raw_items = build_item_candidates(
        db, topic_snapshots, unlocks, completed_ids, sections, p_map,
    )
    raw_hints = build_section_hint_candidates(
        db, topic_snapshots, unlocks, sections, p_map,
    )

    # Score and bucket
    actionable: list[_Scored] = []
    locked_previews: list[_Scored] = []
    revision: list[_Scored] = []
    for cand in raw_items:
        if cand.topic.classification not in (
            SkillTopicClassification.WEAK,
            SkillTopicClassification.NEEDS_REVISION,
            SkillTopicClassification.STRONG,
        ):
            continue
        # Skip uncompleted items in STRONG topics (no need to recommend)
        if not cand.item_completed and cand.topic.classification == SkillTopicClassification.STRONG:
            continue
        scored = _score_item(cand)
        if scored.kind == RecommendationKind.ACTIONABLE:
            actionable.append(scored)
        elif scored.kind == RecommendationKind.LOCKED_PREVIEW:
            locked_previews.append(scored)
        elif scored.kind == RecommendationKind.REVISION:
            revision.append(scored)

    section_hints = [_score_section_hint(h) for h in raw_hints]

    # Rank each bucket
    top_actionable = rank_top_n(
        actionable, key_fn=lambda r: r.item_id,
        score_fn=lambda r: r.score, limit=ACTIONABLE_LIMIT,
    )
    top_locked = _select_locked(section_hints, locked_previews, LOCKED_PREVIEW_LIMIT)
    top_revision = rank_top_n(
        revision, key_fn=lambda r: r.item_id,
        score_fn=lambda r: r.score, limit=REVISION_LIMIT,
    )

    # Cross-kind dedupe on item_id (partial unique index requires one ACTIVE row per item)
    by_item: dict[int, _Scored] = {}
    section_level: list[_Scored] = []
    for r in top_actionable + top_locked + top_revision:
        if r.item_id is None:
            section_level.append(r)
        else:
            existing = by_item.get(r.item_id)
            if existing is None or r.score > existing.score:
                by_item[r.item_id] = r
    final = list(by_item.values()) + section_level

    # Expire existing ACTIVE rows (history preserved via status)
    db.execute(
        update(Recommendation)
        .where(
            Recommendation.user_id == user_id,
            Recommendation.status == RecommendationStatus.ACTIVE,
        )
        .values(status=RecommendationStatus.EXPIRED)
    )

    # Insert new rows
    for r in final:
        db.add(Recommendation(
            user_id=user_id,
            skill_profile_id=skill.id,
            topic_id=r.topic_id,
            section_id=r.section_id,
            item_id=r.item_id,
            kind=r.kind,
            status=RecommendationStatus.ACTIVE,
            score=round(r.score, 4),
            weak_topic_score=round(r.w, 4),
            difficulty_score=round(r.d, 4),
            prerequisite_score=round(r.p, 4),
            target_difficulty=r.target_difficulty,
            reason=r.reason,
        ))
    db.flush()