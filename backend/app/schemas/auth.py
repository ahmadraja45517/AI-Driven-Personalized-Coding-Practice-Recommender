from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    course: str = Field(min_length=2, max_length=120)
    academic_year: int = Field(ge=1, le=8)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("Password must contain at least one letter and one digit")
        return v

    @field_validator("confirm_password")
    @classmethod
    def _passwords_match(cls, v: str, info):
        if v != info.data.get("password"):
            raise ValueError("Passwords do not match")
        return v


class RegisterResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    message: str = "Registration successful"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserMe(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    course: str
    academic_year: int
    created_at: datetime