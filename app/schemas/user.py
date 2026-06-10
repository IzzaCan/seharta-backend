from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict

# Base Schema
class UserBase(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=255)
    email: EmailStr


# Auth Schemas
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserGoogleLogin(BaseModel):
    id_token: str


# Response Schemas
class UserResponse(UserBase):
    id: UUID

    avatar_url: Optional[str] = None
    family_id: Optional[UUID] = None

    is_active: bool
    is_verified: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Token Schemas
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None

    token_type: str = "bearer"
    expires_in: int = 3600

    user: UserResponse


class TokenPayload(BaseModel):
    sub: Optional[str] = None

    exp: Optional[int] = None
    iat: Optional[int] = None

    type: str = "access"