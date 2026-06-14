"""Pydantic schemas for Expense — request and response shapes."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.expense_item import ExpenseItemCreate, ExpenseItemResponse


class ExpenseCreate(BaseModel):
    """Fields required when creating an expense."""

    category_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=1, max_length=255)
    merchant_name: str | None = Field(default=None, max_length=255)
    receipt_number: str | None = Field(default=None, max_length=100)
    receipt_date: date
    payment_method: str | None = Field(default=None, max_length=50)
    currency: str = Field(default="THB")
    subtotal: Decimal | None = Field(default=None, ge=Decimal("0"))
    tax_amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    discount_amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    total_amount: Decimal = Field(..., ge=Decimal("0"))
    notes: str | None = None
    items: list[ExpenseItemCreate] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def title_not_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("title must not be whitespace-only")
        return stripped

    @field_validator("merchant_name", "receipt_number", "payment_method", mode="before")
    @classmethod
    def optional_str_not_whitespace(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field must not be whitespace-only when provided")
        return stripped

    @field_validator("currency")
    @classmethod
    def currency_format(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("currency must be exactly 3 alphabetic characters (e.g. THB, USD)")
        return v


class ExpenseUpdate(BaseModel):
    """All fields optional for partial expense updates."""

    category_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    merchant_name: str | None = Field(default=None, max_length=255)
    receipt_number: str | None = Field(default=None, max_length=100)
    receipt_date: date | None = None
    payment_method: str | None = Field(default=None, max_length=50)
    currency: str | None = None
    subtotal: Decimal | None = Field(default=None, ge=Decimal("0"))
    tax_amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    discount_amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    total_amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    notes: str | None = None
    items: list[ExpenseItemCreate] | None = None

    @field_validator("title")
    @classmethod
    def title_not_whitespace(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("title must not be whitespace-only")
        return stripped

    @field_validator("merchant_name", "receipt_number", "payment_method", mode="before")
    @classmethod
    def optional_str_not_whitespace(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field must not be whitespace-only when provided")
        return stripped

    @field_validator("currency")
    @classmethod
    def currency_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("currency must be exactly 3 alphabetic characters")
        return v


class ExpenseResponse(BaseModel):
    """Safe expense data returned to the client."""

    id: int
    user_id: int
    category_id: int
    title: str
    merchant_name: str | None
    receipt_number: str | None
    receipt_date: date
    payment_method: str | None
    currency: str
    subtotal: Decimal | None
    tax_amount: Decimal | None
    discount_amount: Decimal | None
    total_amount: Decimal
    notes: str | None
    is_confirmed: bool
    created_at: datetime
    updated_at: datetime
    items: list[ExpenseItemResponse] = Field(default_factory=list)
    # deleted_at, ai_raw_response, ai internal fields are intentionally excluded

    model_config = ConfigDict(from_attributes=True)
