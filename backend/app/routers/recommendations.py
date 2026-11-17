from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.recommendations import RecommendationListResponse
from app.services.recommendation_service import generate_recommendations, list_recommendations

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationListResponse)
def list_recommendations_endpoint(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_recommendations(db, user.id)


@router.post("/refresh", response_model=RecommendationListResponse)
def refresh_recommendations_endpoint(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    generate_recommendations(db, user.id)
    db.commit()
    return list_recommendations(db, user.id)