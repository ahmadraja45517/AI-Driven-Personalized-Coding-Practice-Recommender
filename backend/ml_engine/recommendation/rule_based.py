"""Rule-based scoring formulas for the recommendation engine.

Pure functions only. No DB access, no side effects, no logging.
"""
from __future__ import annotations

from app.models.enums import Difficulty, SkillTopicClassification


# --- Configurable thresholds (Decision A) -----------------------------------

WEAK_ACCURACY_THRESHOLD: float = 0.40
STRONG_ACCURACY_THRESHOLD: float = 0.70


# --- Configurable weights (Decision 6) --------------------------------------

WEIGHT_WEAK_TOPIC: float = 0.40
WEIGHT_DIFFICULTY: float = 0.35
WEIGHT_PREREQUISITE: float = 0.25


# --- Difficulty mapping (Decision 6B) ---------------------------------------

_DIFFICULTY_INT = {
    Difficulty.EASY: 0,
    Difficulty.MEDIUM: 1,
    Difficulty.HARD: 2,
}


def difficulty_value(d: Difficulty) -> int:
    """EASY=0, MEDIUM=1, HARD=2."""
    return _DIFFICULTY_INT[d]


# --- Topic classification (Decision A) --------------------------------------

def classify_topic(accuracy: float) -> SkillTopicClassification:
    """<40% WEAK, 40–69% NEEDS_REVISION, >=70% STRONG."""
    if accuracy < WEAK_ACCURACY_THRESHOLD:
        return SkillTopicClassification.WEAK
    if accuracy < STRONG_ACCURACY_THRESHOLD:
        return SkillTopicClassification.NEEDS_REVISION
    return SkillTopicClassification.STRONG


def target_difficulty_for(accuracy: float) -> Difficulty:
    """<40% EASY, 40–69% MEDIUM, >=70% HARD."""
    if accuracy < WEAK_ACCURACY_THRESHOLD:
        return Difficulty.EASY
    if accuracy < STRONG_ACCURACY_THRESHOLD:
        return Difficulty.MEDIUM
    return Difficulty.HARD


# --- Score components (Decision 6) ------------------------------------------

def weak_topic_relevance(accuracy: float) -> float:
    """W = 1 - topic_accuracy, clamped to [0, 1]."""
    return max(0.0, min(1.0, 1.0 - accuracy))


def difficulty_suitability(problem_difficulty: float, target_difficulty: float) -> float:
    """D = 1 - |problem_difficulty - target_difficulty| / 2, clamped to [0, 1].

    Accepts ints or floats so section-level averages can be scored.
    """
    return max(0.0, min(1.0, 1.0 - abs(problem_difficulty - target_difficulty) / 2.0))


def prerequisite_readiness(completed: int, total: int) -> float:
    """P = completed / total. Returns 1.0 when there are no prerequisites."""
    if total <= 0:
        return 1.0
    return max(0.0, min(1.0, completed / total))


def recommendation_score(w: float, d: float, p: float) -> float:
    """R = 0.40·W + 0.35·D + 0.25·P, clamped to [0, 1]."""
    score = WEIGHT_WEAK_TOPIC * w + WEIGHT_DIFFICULTY * d + WEIGHT_PREREQUISITE * p
    return max(0.0, min(1.0, score))