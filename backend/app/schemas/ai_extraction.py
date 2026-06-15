"""Pydantic schemas for Gemini AI receipt extraction output.

These schemas validate and normalise the raw JSON that Gemini returns.
They are not saved directly to the database — the next step maps them
to Expense / ExpenseItem records.

Supported language codes: en, th
Supported currency symbols → codes: ฿ → THB, $ → USD
"""

import math
from datetime import date, time
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Full-word language names that Gemini may return instead of the 2-letter code.
_LANGUAGE_MAP: dict[str, str] = {
    "english": "en",
    "thai": "th",
    "en": "en",
    "th": "th",
}

# Currency symbols Gemini might return.
_CURRENCY_SYMBOL_MAP: dict[str, str] = {
    "฿": "THB",
    "$": "USD",
}


def _normalise_language(value: str) -> str:
    """Convert Gemini language strings to 'en' or 'th', raise ValueError otherwise."""
    normalised = _LANGUAGE_MAP.get(value.strip().lower())
    if normalised is None:
        raise ValueError(
            f"Unsupported language '{value}'. Only 'en' and 'th' are allowed."
        )
    return normalised


def _normalise_currency(value: str) -> str:
    """Uppercase a currency code, or map a known symbol to a code."""
    stripped = value.strip()
    if stripped in _CURRENCY_SYMBOL_MAP:
        return _CURRENCY_SYMBOL_MAP[stripped]
    return stripped.upper()


def _check_decimal(v: Any, field_name: str, allow_negative: bool = False) -> Decimal | None:
    """Parse and validate a Decimal field: reject NaN, Inf, and (optionally) negatives."""
    if v is None:
        return None
    try:
        d = Decimal(str(v))
    except InvalidOperation:
        raise ValueError(f"{field_name} is not a valid decimal number")
    if not d.is_finite():
        raise ValueError(f"{field_name} must not be NaN or infinite")
    if not allow_negative and d < Decimal("0"):
        raise ValueError(f"{field_name} must be zero or greater")
    return d


# ---------------------------------------------------------------------------
# ExtractedReceiptItem
# ---------------------------------------------------------------------------

class ExtractedReceiptItem(BaseModel):
    """One line item extracted from a receipt."""

    original_name: str | None = None
    name_en: str | None = None
    name_th: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    discount_amount: Decimal | None = None
    total_price: Decimal | None = None
    category_name: str | None = None

    # ── String normalisation ──────────────────────────────────────────────

    @field_validator("original_name", "name_en", "name_th", "unit", "category_name", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v: Any) -> Any:
        """Convert empty or whitespace-only strings to None."""
        if isinstance(v, str):
            stripped = v.strip()
            return stripped if stripped else None
        return v

    # ── Decimal validation ────────────────────────────────────────────────

    @field_validator("quantity", mode="before")
    @classmethod
    def _validate_quantity(cls, v: Any) -> Any:
        return _check_decimal(v, "quantity")

    @field_validator("unit_price", mode="before")
    @classmethod
    def _validate_unit_price(cls, v: Any) -> Any:
        return _check_decimal(v, "unit_price")

    @field_validator("discount_amount", mode="before")
    @classmethod
    def _validate_discount_amount(cls, v: Any) -> Any:
        return _check_decimal(v, "discount_amount")

    @field_validator("total_price", mode="before")
    @classmethod
    def _validate_total_price(cls, v: Any) -> Any:
        return _check_decimal(v, "total_price")


# ---------------------------------------------------------------------------
# ExtractedReceiptData
# ---------------------------------------------------------------------------

class ExtractedReceiptData(BaseModel):
    """Full structured data extracted from one receipt image or PDF."""

    title: str | None = None
    merchant_name: str | None = None          # kept for backward compat; mapped to paid_to
    paid_to: str | None = None                # who was paid (person or shop name)
    tax_id: str | None = None                 # tax ID / VAT registration number on receipt
    category_name: str | None = None          # AI-guessed category for the whole expense
    receipt_number: str | None = None
    receipt_date: date | None = None
    receipt_time: time | None = None
    document_type: str | None = None
    payment_method: str | None = None
    currency: str | None = None
    subtotal: Decimal | None = None
    tax_amount: Decimal | None = None
    discount_amount: Decimal | None = None
    total_amount: Decimal  # required
    language_detected: str  # normalised to "en" or "th"
    ai_confidence: Decimal | None = None
    items: list[ExtractedReceiptItem] = Field(default_factory=list)

    # ── String normalisation ──────────────────────────────────────────────

    @field_validator(
        "title", "merchant_name", "paid_to", "tax_id", "category_name",
        "receipt_number", "document_type", "payment_method",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: Any) -> Any:
        if isinstance(v, str):
            stripped = v.strip()
            return stripped if stripped else None
        return v

    # ── Language normalisation ────────────────────────────────────────────

    @field_validator("language_detected", mode="before")
    @classmethod
    def _normalise_language(cls, v: Any) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("language_detected is required")
        return _normalise_language(v)

    # ── Currency normalisation ────────────────────────────────────────────

    @field_validator("currency", mode="before")
    @classmethod
    def _normalise_currency(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return _normalise_currency(str(v))

    # ── Decimal validation ────────────────────────────────────────────────

    @field_validator("total_amount", mode="before")
    @classmethod
    def _validate_total_amount(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("total_amount is required")
        return _check_decimal(v, "total_amount")

    @field_validator("subtotal", mode="before")
    @classmethod
    def _validate_subtotal(cls, v: Any) -> Any:
        return _check_decimal(v, "subtotal")

    @field_validator("tax_amount", mode="before")
    @classmethod
    def _validate_tax_amount(cls, v: Any) -> Any:
        return _check_decimal(v, "tax_amount")

    @field_validator("discount_amount", mode="before")
    @classmethod
    def _validate_discount_amount(cls, v: Any) -> Any:
        return _check_decimal(v, "discount_amount")

    # ── Confidence: 0–1 range; normalise obvious percentages (e.g. 85 → 0.85) ──

    @field_validator("ai_confidence", mode="before")
    @classmethod
    def _validate_confidence(cls, v: Any) -> Any:
        if v is None:
            return None
        try:
            d = Decimal(str(v))
        except InvalidOperation:
            raise ValueError("ai_confidence is not a valid decimal number")
        if not d.is_finite():
            raise ValueError("ai_confidence must not be NaN or infinite")
        # Normalise clear percentage values: integers 2–100 become 0.02–1.00.
        # Values like 1.01 are NOT treated as percentages — they are out of range.
        if d > Decimal("1") and d == d.to_integral_value() and d <= Decimal("100"):
            d = d / Decimal("100")
        if d < Decimal("0") or d > Decimal("1"):
            raise ValueError("ai_confidence must be between 0 and 1")
        return d
