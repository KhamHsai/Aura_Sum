from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

class CategoryCreate(BaseModel):
    name: str  # the user-typed name; stored as name_en and name_th

    @field_validator('name')
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Category name must not be blank')
        return v.strip()

class CategoryResponse(BaseModel):
    id: int
    code: str
    name_en: str
    name_th: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)