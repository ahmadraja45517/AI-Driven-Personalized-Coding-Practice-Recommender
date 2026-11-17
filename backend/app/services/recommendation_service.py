from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Recommendation, Topic, LearningItem, LearningSection
from app.models.enums import RecommendationStatus
from app.schemas.recommendations import RecommendationItem, RecommendationListResponse

try:
    from ml_engine.recommendation.hybrid import ENGINE_AVAILABLE, generate_for_user  # type: ignore
except Exception:  # pragma: no cover - defensive
    ENGINE_AVAILABLE = False
    generate_for_user = None  # type: ignore


def generate_recommendations(db: Session, user_id: int) -> None:
    """Delegate to the ML engine. The backend never invents recommendations itself."""
    if not ENGINE_AVAILABLE or generate_for_user is None:
        return
    generate_for_user(db, user_id)


def list_recommendations(db: Session, user_id: int) -> RecommendationListResponse:
    rows = db.execute(
        select(
            Recommendation, 
            Topic.code, 
            LearningItem.title, 
            LearningItem.external_url,
            LearningSection.title
        )
        .join(Topic, Topic.id == Recommendation.topic_id)
        .outerjoin(LearningItem, LearningItem.id == Recommendation.item_id)
        .outerjoin(LearningSection, LearningSection.id == Recommendation.section_id)
        .where(
            Recommendation.user_id == user_id,
            Recommendation.status == RecommendationStatus.ACTIVE,
        )
        .order_by(Recommendation.score.desc())
    ).all()
    
    items = [
        RecommendationItem(
            id=r.id, kind=r.kind, status=r.status, score=float(r.score),
            weak_topic_score=float(r.weak_topic_score),
            difficulty_score=float(r.difficulty_score),
            prerequisite_score=float(r.prerequisite_score),
            topic=code, 
            section_id=r.section_id, 
            section_title=sec_title,
            item_id=r.item_id, 
            item_title=item_title, 
            item_url=item_url,
            target_difficulty=r.target_difficulty, 
            reason=r.reason,
        ) for r, code, item_title, item_url, sec_title in rows
    ]
    return RecommendationListResponse(engine_available=True, items=items)