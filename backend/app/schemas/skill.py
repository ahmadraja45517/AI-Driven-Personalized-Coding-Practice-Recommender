from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import (
    Difficulty, SkillTopicClassification, SkillTrend, StudentLevel,
)


class SkillTopicEntry(BaseModel):
    topic: str
    accuracy: float | None
    evidence_count: int
    target_difficulty: Difficulty | None
    classification: SkillTopicClassification
    trend: SkillTrend


class SkillProfileResponse(BaseModel):
    profile_id: int
    computed_at: datetime
    demonstrated_level: StudentLevel | None
    recommended_level: StudentLevel | None
    overall_accuracy: float | None
    evidence_count: int
    topics: list[SkillTopicEntry]