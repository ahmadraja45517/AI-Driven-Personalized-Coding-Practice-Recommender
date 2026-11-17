from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.enums import ContentSource, Difficulty, LearningItemKind


class SectionProgress(BaseModel):
    items_total: int
    items_completed: int
    items_required_threshold: int
    completion_ratio: float
    passes_completion: bool
    best_assessment_pct: float | None
    assessment_pass_threshold_pct: float
    passes_assessment: bool
    requirements_met: bool


class SectionSummary(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None
    order_index: int
    content_status: str
    status: str  # UNLOCKED | LOCKED | COMPLETED
    progress: SectionProgress | None


class SectionListResponse(BaseModel):
    enrolled: bool
    sections: list[SectionSummary]


class ItemForSection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    kind: LearningItemKind
    source: ContentSource
    difficulty: Difficulty | None
    content_md: str | None
    external_url: str | None
    estimated_minutes: int | None
    is_completed: bool
    completed_at: str | None


class SectionDetailResponse(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None
    status: str
    items: list[ItemForSection]