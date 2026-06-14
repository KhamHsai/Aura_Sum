from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class CategoryResponse(BaseModel):
    id: int
    code: str
    name_en: str
    name_th: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)