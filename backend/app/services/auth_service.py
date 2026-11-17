from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest


class AuthError(Exception):
    """Raised for authentication / registration failures."""


def register(db: Session, req: RegisterRequest) -> User:
    email = req.email.lower()
    existing = db.execute(select(User).where(func.lower(User.email) == email)).scalar_one_or_none()
    if existing is not None:
        raise AuthError("An account with this email already exists")

    user = User(
        email=email,
        password_hash=hash_password(req.password),
        full_name=req.full_name.strip(),
        course=req.course.strip(),
        academic_year=req.academic_year,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("An account with this email already exists") from exc
    db.refresh(user)
    return user


def login(db: Session, req: LoginRequest) -> str:
    user = db.execute(
        select(User).where(func.lower(User.email) == req.email.lower())
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise AuthError("Invalid email or password")
    if not verify_password(req.password, user.password_hash):
        raise AuthError("Invalid email or password")
    return create_access_token(user.id)