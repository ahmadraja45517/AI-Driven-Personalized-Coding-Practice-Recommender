from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.profile import (
    EnrollRoadmapRequest, EnrollRoadmapResponse, OnboardingRequest,
    ProfileResponse, ProfileUpdate,
)
from app.services.profile_service import (
    ProfileError, complete_onboarding, enroll_in_roadmap, get_profile, update_profile,
)

router = APIRouter(prefix="/api/v1", tags=["profile"])


@router.get("/profile", response_model=ProfileResponse)
def get_profile_endpoint(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_profile(db, user)


@router.put("/profile", response_model=ProfileResponse)
def update_profile_endpoint(
    req: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    return update_profile(db, user, req)


@router.post("/onboarding", response_model=ProfileResponse)
def onboarding_endpoint(
    req: OnboardingRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    return complete_onboarding(db, user, req)


@router.post("/roadmap/enroll", response_model=EnrollRoadmapResponse)
def enroll_endpoint(
    req: EnrollRoadmapRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    from app.models.enums import StudentLevel
    if req.level != StudentLevel.BEGINNER:
        raise HTTPException(status_code=400, detail="Only the Beginner roadmap is available in this version")
    try:
        return enroll_in_roadmap(db, user)
    except ProfileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc