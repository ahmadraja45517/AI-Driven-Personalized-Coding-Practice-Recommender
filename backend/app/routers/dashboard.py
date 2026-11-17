from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import build_dashboard

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def dashboard_endpoint(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_dashboard(db, user)