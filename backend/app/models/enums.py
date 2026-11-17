from __future__ import annotations

import enum
from typing import Type

import sqlalchemy as sa


class PreferredLanguage(str, enum.Enum):
    JAVA = "JAVA"
    CPP = "CPP"
    PYTHON = "PYTHON"


class StudentLevel(str, enum.Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class Difficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"

    @property
    def numeric(self) -> int:
        """Used by the recommendation engine's D = 1 - |d_problem - d_target| / 2."""
        return {"EASY": 0, "MEDIUM": 1, "HARD": 2}[self.value]


class LearningItemKind(str, enum.Enum):
    LESSON = "LESSON"
    EXTERNAL_PROBLEM = "EXTERNAL_PROBLEM"


class ContentSource(str, enum.Enum):
    INTERNAL = "INTERNAL"
    LEETCODE = "LEETCODE"


class SectionContentStatus(str, enum.Enum):
    PUBLISHED = "PUBLISHED"   # has real content
    PLANNED = "PLANNED"       # future / coming soon, never accessible


class AssessmentKind(str, enum.Enum):
    DIAGNOSTIC = "DIAGNOSTIC"
    SECTION_END = "SECTION_END"


class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    ABANDONED = "ABANDONED"


class SkillTopicClassification(str, enum.Enum):
    STRONG = "STRONG"
    WEAK = "WEAK"
    NEEDS_REVISION = "NEEDS_REVISION"
    IMPROVING = "IMPROVING"
    STRUGGLING = "STRUGGLING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class SkillTrend(str, enum.Enum):
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"


class RecommendationKind(str, enum.Enum):
    ACTIONABLE = "ACTIONABLE"         # student may act on it now
    LOCKED_PREVIEW = "LOCKED_PREVIEW" # shown with reason, no access
    REVISION = "REVISION"             # previously completed work


class RecommendationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISMISSED = "DISMISSED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class UnlockStatus(str, enum.Enum):
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    COMPLETED = "COMPLETED"


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


def pg_enum(enum_cls: Type[enum.Enum], name: str) -> sa.Enum:
    """Native PG enum that stores the *value*, not the member name."""
    return sa.Enum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=lambda e: [m.value for m in e],
    )