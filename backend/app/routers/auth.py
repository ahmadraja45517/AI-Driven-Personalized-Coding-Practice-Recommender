from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.auth import (
    LoginRequest, RegisterRequest, RegisterResponse, TokenResponse, UserMe,
)
from app.services.auth_service import AuthError, login, register

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register_endpoint(req: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = register(db, req)
    except AuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RegisterResponse(id=user.id, email=user.email, full_name=user.full_name)


@router.post("/login", response_model=TokenResponse)
def login_endpoint(req: LoginRequest, db: Session = Depends(get_db)):
    try:
        token = login(db, req)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return TokenResponse(
        access_token=token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserMe)
def me(user: User = Depends(get_current_user)):
    return UserMe(
        id=user.id, email=user.email, full_name=user.full_name,
        course=user.course, academic_year=user.academic_year, created_at=user.created_at,
    )