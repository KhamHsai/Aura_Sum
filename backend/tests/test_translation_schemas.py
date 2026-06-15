"""Tests for translation request/response schemas.

No database, no network calls.
"""

import pytest
from pydantic import ValidationError

from app.schemas.translation import (
    ExpenseTranslationRequest,
    ExpenseTranslationResponse,
    GeminiTranslationResult,
    GeminiTranslatedItem,
    TranslatedExpenseItem,
)


# ── 1. Request accepts "en" ───────────────────────────────────────────────────

def test_request_accepts_en():
    req = ExpenseTranslationRequest(target_language="en")
    assert req.target_language == "en"


# ── 2. Request accepts "th" ───────────────────────────────────────────────────

def test_request_accepts_th():
    req = ExpenseTranslationRequest(target_language="th")
    assert req.target_language == "th"


# ── 3. Uppercase "EN" normalises to "en" ─────────────────────────────────────

def test_uppercase_en_normalises():
    req = ExpenseTranslationRequest(target_language="EN")
    assert req.target_language == "en"


# ── 4. Uppercase "TH" normalises to "th" ─────────────────────────────────────

def test_uppercase_th_normalises():
    req = ExpenseTranslationRequest(target_language="TH")
    assert req.target_language == "th"


# ── 5. Unsupported language "fr" is rejected with 422 ────────────────────────

def test_unsupported_language_rejected():
    with pytest.raises(ValidationError):
        ExpenseTranslationRequest(target_language="fr")


# ── 6. Unsupported language "zh" is rejected ────────────────────────────────

def test_unsupported_language_zh_rejected():
    with pytest.raises(ValidationError):
        ExpenseTranslationRequest(target_language="zh")


# ── 7. Valid translation response is accepted ────────────────────────────────

def test_valid_translation_response_accepted():
    resp = ExpenseTranslationResponse(
        expense_id=1,
        source_language="en",
        target_language="th",
        translated_title="ข้าวผัด",
        translated_notes=None,
        items=[],
        reused_existing_translation=False,
    )
    assert resp.expense_id == 1
    assert resp.translated_title == "ข้าวผัด"


# ── 8. Empty item list is accepted ───────────────────────────────────────────

def test_empty_item_list_accepted():
    resp = ExpenseTranslationResponse(
        expense_id=1,
        source_language="th",
        target_language="en",
        items=[],
    )
    assert resp.items == []


# ── 9. Translated item with all fields is accepted ───────────────────────────

def test_translated_item_all_fields_accepted():
    item = TranslatedExpenseItem(
        item_id=5,
        original_name="กาแฟ",
        name_en="Coffee",
        name_th="กาแฟ",
        translated_name="Coffee",
    )
    assert item.item_id == 5
    assert item.translated_name == "Coffee"


# ── 10. Translated item with null fields is accepted ─────────────────────────

def test_translated_item_null_fields_accepted():
    item = TranslatedExpenseItem(item_id=3)
    assert item.original_name is None
    assert item.name_en is None
    assert item.translated_name is None


# ── 11. reused_existing_translation defaults to False ────────────────────────

def test_reused_existing_translation_defaults_false():
    resp = ExpenseTranslationResponse(
        expense_id=2,
        source_language="en",
        target_language="th",
    )
    assert resp.reused_existing_translation is False


# ── 12. GeminiTranslationResult accepts valid payload ────────────────────────

def test_gemini_result_accepts_valid_payload():
    result = GeminiTranslationResult(
        translated_title="สวัสดี",
        translated_notes=None,
        items=[GeminiTranslatedItem(item_id=1, translated_name="กาแฟ")],
    )
    assert result.translated_title == "สวัสดี"
    assert len(result.items) == 1


# ── 13. GeminiTranslationResult accepts empty items ──────────────────────────

def test_gemini_result_accepts_empty_items():
    result = GeminiTranslationResult(
        translated_title="Hello",
        items=[],
    )
    assert result.items == []


# ── 14. validate_item_ids rejects extra item IDs ─────────────────────────────

def test_validate_item_ids_rejects_extra_ids():
    result = GeminiTranslationResult(
        items=[
            GeminiTranslatedItem(item_id=1, translated_name="a"),
            GeminiTranslatedItem(item_id=99, translated_name="b"),  # unexpected
        ]
    )
    with pytest.raises(ValueError, match="unexpected item IDs"):
        result.validate_item_ids([1])


# ── 15. validate_item_ids rejects missing item IDs ───────────────────────────

def test_validate_item_ids_rejects_missing_ids():
    result = GeminiTranslationResult(
        items=[GeminiTranslatedItem(item_id=1, translated_name="a")]
    )
    with pytest.raises(ValueError, match="did not return"):
        result.validate_item_ids([1, 2])


# ── 16. validate_item_ids passes when IDs match exactly ──────────────────────

def test_validate_item_ids_passes_when_exact_match():
    result = GeminiTranslationResult(
        items=[
            GeminiTranslatedItem(item_id=1, translated_name="a"),
            GeminiTranslatedItem(item_id=2, translated_name="b"),
        ]
    )
    result.validate_item_ids([1, 2])  # should not raise


# ── 17. validate_item_ids passes when no items expected and none returned ─────

def test_validate_item_ids_passes_empty():
    result = GeminiTranslationResult(items=[])
    result.validate_item_ids([])  # should not raise


# ── 18. English and Thai values are stored separately ────────────────────────

def test_english_and_thai_values_stay_separate():
    item = TranslatedExpenseItem(
        item_id=10,
        name_en="Rice",
        name_th="ข้าว",
        translated_name="ข้าว",
    )
    assert item.name_en == "Rice"
    assert item.name_th == "ข้าว"


# ── 19. Response does not expose sensitive internal fields ───────────────────

def test_response_does_not_expose_internal_fields():
    resp = ExpenseTranslationResponse(
        expense_id=1,
        source_language="en",
        target_language="th",
    )
    data = resp.model_dump()
    for field in ("user_id", "api_key", "file_path", "deleted_at", "ai_raw_response"):
        assert field not in data


# ── 20. Request rejects empty string ─────────────────────────────────────────

def test_request_rejects_empty_string():
    with pytest.raises(ValidationError):
        ExpenseTranslationRequest(target_language="")
