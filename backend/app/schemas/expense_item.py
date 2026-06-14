"""Pydantic schemas for ExpenseItem — request and response shapes."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExpenseItemCreate(BaseModel):
    """Fields required when creating one expense item."""

    original_name: str = Field(..., min_length=1, max_length=255)
    name_en: str | None = Field(default=None, max_length=255)
    name_th: str | None = Field(default=None, max_length=255)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    unit: str | None = Field(default=None, max_length=30)
    unit_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    discount_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    total_price: Decimal = Field(..., ge=Decimal("0"))
    category_id: int | None = Field(default=None, gt=0)

    @field_validator("original_name")
    @classmethod
    def name_not_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("original_name must not be whitespace-only")
        return stripped

    @field_validator("name_en", "name_th", mode="before")
    @classmethod
    def optional_str_not_whitespace(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            return None
        return stripped


class ExpenseItemUpdate(BaseModel):
    """All fields optional for partial item updates."""

    original_name: str | None = Field(default=None, min_length=1, max_length=255)
    name_en: str | None = Field(default=None, max_length=255)
    name_th: str | None = Field(default=None, max_length=255)
    quantity: Decimal | None = Field(default=None, gt=Decimal("0"))
    unit: str | None = Field(default=None, max_length=30)
    unit_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    discount_amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    total_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    category_id: int | None = Field(default=None, gt=0)

    @field_validator("original_name")
    @classmethod
    def name_not_whitespace(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("original_name must not be whitespace-only")
        return stripped


class ExpenseItemResponse(BaseModel):
    """Safe expense-item data returned to the client."""

    id: int
    expense_id: int
    category_id: int | None
    original_name: str
    name_en: str | None
    name_th: str | None
    quantity: Decimal
    unit: str | None
    unit_price: Decimal | None
    discount_amount: Decimal
    total_price: Decimal
    created_at: datetime
    updated_at: datetime
    # deleted_at is intentionally excluded

    model_config = ConfigDict(from_attributes=True)
