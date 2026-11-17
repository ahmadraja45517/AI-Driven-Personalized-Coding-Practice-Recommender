from __future__ import annotations

from pydantic import BaseModel

from app.schemas.assessments import AssessmentSummary
from app.schemas.profile import LevelRecommendation
from app.schemas.recommendations import RecommendationItem
from app.schemas.sections import SectionSummary
from app.schemas.skill import SkillProfileResponse
from app.models.enums import PreferredLanguage, StudentLevel


class ProgressSummary(BaseModel):
    total_items: int
    completed_items: int
    completion_ratio: float
    current_section: str | None
    unlocked_sections: int
    completed_sections: int


class DiagnosticHistory(BaseModel):
    first_pct: float | None
    latest_pct: float | None
    best_pct: float | None
    attempts_count: int


class DashboardResponse(BaseModel):
    full_name: str
    preferred_language: PreferredLanguage | None
    selected_level: StudentLevel | None
    demonstrated_level: StudentLevel | None
    recommended_level: StudentLevel | None
    level_recommendation: LevelRecommendation
    progress: ProgressSummary
    sections: list[SectionSummary]
    diagnostic_history: DiagnosticHistory | None
    section_assessments: list[AssessmentSummary]
    skill_profile: SkillProfileResponse | None
    recommendations: list[RecommendationItem]