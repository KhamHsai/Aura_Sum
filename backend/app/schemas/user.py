from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    preferred_language: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=255)
    preferred_language: Optional[Literal["en", "th"]] = None

    @field_validator("username", "full_name", mode="before")
    @classmethod
    def trim_strings(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return v.strip()
        return v
