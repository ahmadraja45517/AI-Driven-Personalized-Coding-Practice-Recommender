from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.sections import SectionDetailResponse, SectionListResponse
from app.services.section_service import get_section_detail, list_sections

router = APIRouter(prefix="/api/v1/sections", tags=["sections"])


@router.get("", response_model=SectionListResponse)
def list_sections_endpoint(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_sections(db, user.id)


@router.get("/{section_id}", response_model=SectionDetailResponse)
def get_section_endpoint(
    section_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    try:
        return get_section_detail(db, user.id, section_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/{section_id}/questions", response_model=SectionDetailResponse)
def get_section_questions_endpoint(
    section_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    try:
        return get_section_detail(db, user.id, section_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc