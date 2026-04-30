from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """Bearer access token response fields."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")


class UserBase(BaseModel):
    """Common user fields shared by auth schemas."""

    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr


class UserCreate(UserBase):
    """Request body for user registration."""

    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Request body for username/password login."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)


class UserRead(UserBase):
    """Public user profile returned by the API."""

    id: str
    is_active: bool = True
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class AuthResponse(Token):
    """Response containing an access token and the authenticated user profile."""

    user: UserRead
    model_config = {"from_attributes": True}
