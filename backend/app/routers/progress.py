from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.progress import ProgressUpdateRequest, ProgressUpdateResponse
from app.services.progress_service import ProgressError, set_item_completion

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])


@router.patch("/{item_id}", response_model=ProgressUpdateResponse)
def update_progress_endpoint(
    item_id: int, req: ProgressUpdateRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    try:
        return set_item_completion(db, user.id, item_id, req.is_completed)
    except ProgressError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc