from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.skill import SkillProfileResponse
from app.services.skill_service import get_current_skill_profile

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


@router.get("", response_model=SkillProfileResponse)
def get_skills_endpoint(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    skill = get_current_skill_profile(db, user.id)
    if skill is None:
        raise HTTPException(status_code=404, detail="No skill profile yet")
    return skill