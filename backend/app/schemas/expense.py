"""Pydantic schemas for Expense — request and response shapes."""

from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.expense_item import ExpenseItemCreate, ExpenseItemResponse


class ExpenseCreate(BaseModel):
    """Fields for creating an expense manually."""

    category_id: int | None = Field(default=None, gt=0)   # optional — AI or user fills later
    paid_to: str | None = Field(default=None, max_length=255)
    tax_id: str | None = Field(default=None, max_length=50)
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

    @field_validator("paid_to", "receipt_number", "payment_method", "tax_id", mode="before")
    @classmethod
    def optional_str_not_whitespace(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        return stripped if stripped else None

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
    paid_to: str | None = Field(default=None, max_length=255)
    tax_id: str | None = Field(default=None, max_length=50)
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

    @field_validator("paid_to", "receipt_number", "payment_method", "tax_id", mode="before")
    @classmethod
    def optional_str_not_whitespace(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        return stripped if stripped else None

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
    category_id: int | None
    category_name: str | None = None   # resolved name or AI-guessed name; not persisted
    paid_to: str | None
    tax_id: str | None
    receipt_number: str | None
    receipt_date: date
    receipt_time: time | None
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

    model_config = ConfigDict(from_attributes=True)
