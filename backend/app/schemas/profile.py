from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import PreferredLanguage, StudentLevel


class OnboardingRequest(BaseModel):
    preferred_language: PreferredLanguage
    selected_level: StudentLevel


class ProfileUpdate(BaseModel):
    preferred_language: PreferredLanguage | None = None
    selected_level: StudentLevel | None = None


class LevelRecommendation(BaseModel):
    show: bool
    recommended_level: StudentLevel | None = None
    demonstrated_level: StudentLevel | None = None
    message: str | None = None


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    course: str
    academic_year: int
    preferred_language: PreferredLanguage | None
    selected_level: StudentLevel | None
    onboarding_completed_at: datetime | None
    demonstrated_level: StudentLevel | None
    recommended_level: StudentLevel | None
    level_recommendation: LevelRecommendation


class EnrollRoadmapRequest(BaseModel):
    level: StudentLevel


class EnrollRoadmapResponse(BaseModel):
    enrollment_id: int
    roadmap_level: StudentLevel
    status: str