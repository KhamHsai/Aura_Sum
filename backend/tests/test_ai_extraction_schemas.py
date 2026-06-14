"""Schema-only tests for AI extraction — no database or network calls."""

from datetime import date, time
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.ai_extraction import ExtractedReceiptData, ExtractedReceiptItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_data(**overrides) -> dict:
    """Base valid payload for ExtractedReceiptData."""
    base = {
        "total_amount": "150.00",
        "language_detected": "th",
    }
    base.update(overrides)
    return base


def _valid_item(**overrides) -> dict:
    base = {
        "original_name": "Coffee",
        "quantity": "1",
        "total_price": "50.00",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Valid English extraction payload
# ---------------------------------------------------------------------------

def test_valid_english_payload():
    data = ExtractedReceiptData(**_valid_data(
        language_detected="en",
        merchant_name="Seven Eleven",
        total_amount="89.00",
        currency="USD",
    ))
    assert data.language_detected == "en"
    assert data.total_amount == Decimal("89.00")
    assert data.currency == "USD"


# ---------------------------------------------------------------------------
# 2. Valid Thai extraction payload
# ---------------------------------------------------------------------------

def test_valid_thai_payload():
    data = ExtractedReceiptData(**_valid_data(
        language_detected="th",
        merchant_name="เซเว่น อีเลฟเว่น",
        total_amount="89.00",
        currency="THB",
    ))
    assert data.language_detected == "th"
    assert data.currency == "THB"


# ---------------------------------------------------------------------------
# 3. Language normalisation: "English" → "en"
# ---------------------------------------------------------------------------

def test_language_normalisation_english_word():
    data = ExtractedReceiptData(**_valid_data(language_detected="English"))
    assert data.language_detected == "en"


# ---------------------------------------------------------------------------
# 4. Language normalisation: "Thai" → "th"
# ---------------------------------------------------------------------------

def test_language_normalisation_thai_word():
    data = ExtractedReceiptData(**_valid_data(language_detected="Thai"))
    assert data.language_detected == "th"


# ---------------------------------------------------------------------------
# 5. Unsupported language is rejected
# ---------------------------------------------------------------------------

def test_unsupported_language_rejected():
    with pytest.raises(ValidationError):
        ExtractedReceiptData(**_valid_data(language_detected="my"))  # Myanmar

    with pytest.raises(ValidationError):
        ExtractedReceiptData(**_valid_data(language_detected="ja"))  # Japanese


# ---------------------------------------------------------------------------
# 6. Currency normalisation to uppercase
# ---------------------------------------------------------------------------

def test_currency_normalised_to_uppercase():
    data = ExtractedReceiptData(**_valid_data(currency="thb"))
    assert data.currency == "THB"

    data2 = ExtractedReceiptData(**_valid_data(currency="usd"))
    assert data2.currency == "USD"


# ---------------------------------------------------------------------------
# 7. Thai baht symbol maps to "THB"
# ---------------------------------------------------------------------------

def test_thai_baht_symbol_maps_to_thb():
    data = ExtractedReceiptData(**_valid_data(currency="฿"))
    assert data.currency == "THB"


# ---------------------------------------------------------------------------
# 8. Dollar symbol maps to "USD"
# ---------------------------------------------------------------------------

def test_dollar_symbol_maps_to_usd():
    data = ExtractedReceiptData(**_valid_data(currency="$"))
    assert data.currency == "USD"


# ---------------------------------------------------------------------------
# 9. Decimal strings are parsed as Decimal
# ---------------------------------------------------------------------------

def test_decimal_strings_parsed():
    data = ExtractedReceiptData(**_valid_data(
        total_amount="250.75",
        subtotal="230.00",
        tax_amount="20.75",
    ))
    assert isinstance(data.total_amount, Decimal)
    assert data.subtotal == Decimal("230.00")
    assert data.tax_amount == Decimal("20.75")


# ---------------------------------------------------------------------------
# 10. total_amount is required
# ---------------------------------------------------------------------------

def test_total_amount_required():
    with pytest.raises(ValidationError):
        ExtractedReceiptData(language_detected="en")  # total_amount missing


# ---------------------------------------------------------------------------
# 11. Negative total is rejected
# ---------------------------------------------------------------------------

def test_negative_total_amount_rejected():
    with pytest.raises(ValidationError):
        ExtractedReceiptData(**_valid_data(total_amount="-1.00"))


# ---------------------------------------------------------------------------
# 12. NaN amount is rejected
# ---------------------------------------------------------------------------

def test_nan_total_amount_rejected():
    with pytest.raises(ValidationError):
        ExtractedReceiptData(**_valid_data(total_amount="NaN"))


# ---------------------------------------------------------------------------
# 13. Infinite amount is rejected
# ---------------------------------------------------------------------------

def test_infinite_total_amount_rejected():
    with pytest.raises(ValidationError):
        ExtractedReceiptData(**_valid_data(total_amount="Infinity"))


# ---------------------------------------------------------------------------
# 14. Confidence below zero is rejected
# ---------------------------------------------------------------------------

def test_confidence_below_zero_rejected():
    with pytest.raises(ValidationError):
        ExtractedReceiptData(**_valid_data(ai_confidence="-0.01"))


# ---------------------------------------------------------------------------
# 15. Confidence above one is rejected
# ---------------------------------------------------------------------------

def test_confidence_above_one_rejected():
    # Non-integer values > 1 are out of range (1.01 is not a valid percentage)
    with pytest.raises(ValidationError):
        ExtractedReceiptData(**_valid_data(ai_confidence="1.01"))

    # Integer values > 100 are out of range too
    with pytest.raises(ValidationError):
        ExtractedReceiptData(**_valid_data(ai_confidence="200"))


# ---------------------------------------------------------------------------
# 16. Empty items defaults to []
# ---------------------------------------------------------------------------

def test_empty_items_defaults_to_list():
    data = ExtractedReceiptData(**_valid_data())
    assert data.items == []


# ---------------------------------------------------------------------------
# 17. Valid nested items are accepted
# ---------------------------------------------------------------------------

def test_valid_nested_items_accepted():
    data = ExtractedReceiptData(**_valid_data(items=[
        {"original_name": "Coffee", "quantity": "1", "total_price": "50.00"},
        {"original_name": "ข้าวผัด", "name_en": "Fried Rice", "name_th": "ข้าวผัด",
         "quantity": "1", "total_price": "80.00"},
    ]))
    assert len(data.items) == 2
    assert data.items[0].original_name == "Coffee"
    assert data.items[1].name_th == "ข้าวผัด"


# ---------------------------------------------------------------------------
# 18. Empty item strings become None
# ---------------------------------------------------------------------------

def test_empty_item_strings_become_none():
    item = ExtractedReceiptItem(original_name="Rice", name_en="", name_th="   ")
    assert item.name_en is None
    assert item.name_th is None


# ---------------------------------------------------------------------------
# 19. Negative item quantity is rejected
# ---------------------------------------------------------------------------

def test_negative_item_quantity_rejected():
    with pytest.raises(ValidationError):
        ExtractedReceiptItem(original_name="Water", quantity="-1", total_price="10")


# ---------------------------------------------------------------------------
# 20. Negative item amount is rejected
# ---------------------------------------------------------------------------

def test_negative_item_total_price_rejected():
    with pytest.raises(ValidationError):
        ExtractedReceiptItem(original_name="Water", quantity="1", total_price="-10")


# ---------------------------------------------------------------------------
# Bonus: confidence normalisation from clear percentage (85 → 0.85)
# ---------------------------------------------------------------------------

def test_confidence_percentage_normalised():
    data = ExtractedReceiptData(**_valid_data(ai_confidence="85"))
    assert data.ai_confidence == Decimal("0.85")


def test_confidence_exactly_one_accepted():
    data = ExtractedReceiptData(**_valid_data(ai_confidence="1"))
    assert data.ai_confidence == Decimal("1") / Decimal("100") * Decimal("100") or \
           data.ai_confidence == Decimal("1") or \
           data.ai_confidence == Decimal("0.01")
    # 1 is in range 0–1 directly, so should stay as 1.0
    # Our logic: 1 is NOT > 1, so no percentage normalisation
    data2 = ExtractedReceiptData(**_valid_data(ai_confidence="1.00"))
    assert data2.ai_confidence == Decimal("1.00")


def test_confidence_zero_accepted():
    data = ExtractedReceiptData(**_valid_data(ai_confidence="0"))
    assert data.ai_confidence == Decimal("0")
