from typing import Optional, Literal
from pydantic import BaseModel, Field, EmailStr, field_validator

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    preferred_language: Literal["en", "th"] = "en"

    @field_validator("username", mode="before")
    @classmethod
    def trim_username(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("full_name", mode="before")
    @classmethod
    def trim_full_name(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)

class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)
