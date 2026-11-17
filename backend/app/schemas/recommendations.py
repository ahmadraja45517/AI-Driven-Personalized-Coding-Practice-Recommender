from pydantic import BaseModel

from app.models.enums import Difficulty, RecommendationKind, RecommendationStatus


class RecommendationItem(BaseModel):
    id: int
    kind: RecommendationKind
    status: RecommendationStatus
    score: float
    weak_topic_score: float
    difficulty_score: float
    prerequisite_score: float
    topic: str
    section_id: int | None
    section_title: str | None  # <-- ADD THIS
    item_id: int | None
    item_title: str | None     # <-- ADD THIS
    item_url: str | None       # <-- ADD THIS
    target_difficulty: Difficulty | None
    reason: str


class RecommendationListResponse(BaseModel):
    engine_available: bool
    items: list[RecommendationItem]