from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.assessments import (
    AssessmentForStudent, AssessmentSubmitRequest, AssessmentSummary,
    AttemptHistoryItem, AttemptResult,
)
from app.services.assessment_service import (
    AssessmentError, get_assessment_for_student, get_attempt_detail,
    list_assessments, list_attempts, submit_assessment,
)

router = APIRouter(prefix="/api/v1/assessments", tags=["assessments"])


@router.get("", response_model=list[AssessmentSummary])
def list_assessments_endpoint(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_assessments(db, user.id)


@router.get("/attempts/{attempt_id}", response_model=AttemptResult)
def get_attempt_endpoint(
    attempt_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    try:
        return get_attempt_detail(db, user.id, attempt_id)
    except AssessmentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{assessment_id}", response_model=AssessmentForStudent)
def get_assessment_endpoint(
    assessment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    try:
        return get_assessment_for_student(db, user.id, assessment_id)
    except AssessmentError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/{assessment_id}/attempts", response_model=list[AttemptHistoryItem])
def list_attempts_endpoint(
    assessment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    return list_attempts(db, user.id, assessment_id)


@router.post("/{assessment_id}/submit", response_model=AttemptResult)
def submit_assessment_endpoint(
    assessment_id: int, req: AssessmentSubmitRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    try:
        return submit_assessment(db, user.id, assessment_id, req)
    except AssessmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc