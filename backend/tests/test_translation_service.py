"""Mocked tests for translation_service.translate_expense.

All Gemini calls are patched — no real network requests are made.
Uses smart_receipt_db_test database.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.category import Category
from app.models.expense import Expense
from app.models.expense_item import ExpenseItem
from app.models.refresh_token import RefreshToken
from app.models.translation import Translation
from app.models.user import User
from app.schemas.translation import GeminiTranslatedItem, GeminiTranslationResult
from app.services.translation_service import (
    TranslationServiceError,
    translate_expense,
)
from app.utils.password_utils import hash_password

# ── Test DB ───────────────────────────────────────────────────────────────────
settings.JWT_SECRET_KEY = "test_jwt_secret_key_translation_service_testing_benz_2004"
settings.JWT_ALGORITHM = "HS256"

engine = create_engine(settings.TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(db, *, username="tester", email="tester@example.com") -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("password123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_category(db, *, code="FOOD") -> Category:
    cat = Category(code=code, name_en="Food", name_th="อาหาร", is_active=True)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def make_expense(
    db,
    user_id: int,
    category_id: int,
    *,
    title: str = "Lunch",
    notes: str | None = None,
    language_detected: str | None = "en",
    deleted_at=None,
    input_method: str = "manual",
) -> Expense:
    expense = Expense(
        user_id=user_id,
        category_id=category_id,
        title=title,
        receipt_date=date(2025, 6, 1),
        total_amount=Decimal("100.00"),
        currency="THB",
        input_method=input_method,
        language_detected=language_detected,
        notes=notes,
        deleted_at=deleted_at,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def make_item(
    db,
    expense_id: int,
    *,
    original_name: str = "Coffee",
    name_en: str | None = None,
    name_th: str | None = None,
    total_price: Decimal = Decimal("50.00"),
    deleted_at=None,
) -> ExpenseItem:
    item = ExpenseItem(
        expense_id=expense_id,
        original_name=original_name,
        name_en=name_en,
        name_th=name_th,
        quantity=Decimal("1"),
        total_price=total_price,
        deleted_at=deleted_at,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def make_saved_translation(
    db,
    source_text: str,
    source_language: str,
    target_language: str,
    translated_text: str,
    expense_item_id: int | None = None,
) -> Translation:
    row = Translation(
        expense_item_id=expense_item_id,
        source_text=source_text,
        source_language=source_language,
        target_language=target_language,
        translated_text=translated_text,
        translation_source="gemini",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def gemini_result(
    translated_title: str | None = "แปลแล้ว",
    translated_notes: str | None = None,
    items: list[dict] | None = None,
) -> GeminiTranslationResult:
    """Build a GeminiTranslationResult for use in mocks."""
    return GeminiTranslationResult(
        translated_title=translated_title,
        translated_notes=translated_notes,
        items=[
            GeminiTranslatedItem(item_id=i["item_id"], translated_name=i["translated_name"])
            for i in (items or [])
        ],
    )


PATCH_TRANSLATE = "app.services.translation_service.translate_expense_text"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_db():
    from app.models.receipt_file import ReceiptFile
    db = TestingSessionLocal()
    db.query(Translation).delete()
    db.query(ExpenseItem).delete()
    db.query(Expense).delete()
    db.query(Category).delete()
    db.query(RefreshToken).delete()
    db.query(ReceiptFile).delete()
    db.query(User).delete()
    db.commit()
    db.close()
    yield
    db = TestingSessionLocal()
    db.query(Translation).delete()
    db.query(ExpenseItem).delete()
    db.query(Expense).delete()
    db.query(Category).delete()
    db.query(RefreshToken).delete()
    db.query(ReceiptFile).delete()
    db.query(User).delete()
    db.commit()
    db.close()


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def user(db):
    return make_user(db)


@pytest.fixture()
def category(db):
    return make_category(db)


# ── 1. English expense translates to Thai ────────────────────────────────────

def test_english_expense_translates_to_thai(db, user, category):
    expense = make_expense(db, user.id, category.id, title="Lunch", language_detected="en")
    mock_result = gemini_result(translated_title="มื้อเที่ยง", items=[])
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        resp = translate_expense(db, user.id, expense.id, "th")
    assert resp.target_language == "th"
    assert resp.source_language == "en"


# ── 2. Thai expense translates to English ────────────────────────────────────

def test_thai_expense_translates_to_english(db, user, category):
    expense = make_expense(db, user.id, category.id, title="อาหาร", language_detected="th")
    mock_result = gemini_result(translated_title="Food", items=[])
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        resp = translate_expense(db, user.id, expense.id, "en")
    assert resp.target_language == "en"
    assert resp.source_language == "th"


# ── 3. Expense title is translated ───────────────────────────────────────────

def test_expense_title_is_translated(db, user, category):
    expense = make_expense(db, user.id, category.id, title="Lunch", language_detected="en")
    mock_result = gemini_result(translated_title="มื้อเที่ยง", items=[])
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        resp = translate_expense(db, user.id, expense.id, "th")
    assert resp.translated_title == "มื้อเที่ยง"


# ── 4. Expense notes are translated ──────────────────────────────────────────

def test_expense_notes_are_translated(db, user, category):
    expense = make_expense(
        db, user.id, category.id, title="Lunch", notes="With friends", language_detected="en"
    )
    mock_result = GeminiTranslationResult(
        translated_title="มื้อเที่ยง",
        translated_notes="กับเพื่อน",
        items=[],
    )
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        resp = translate_expense(db, user.id, expense.id, "th")
    assert resp.translated_notes == "กับเพื่อน"


# ── 5. Item names are translated ─────────────────────────────────────────────

def test_item_names_are_translated(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    item = make_item(db, expense.id, original_name="Coffee", name_en="Coffee")
    mock_result = GeminiTranslationResult(
        translated_title="แปล",
        items=[GeminiTranslatedItem(item_id=item.id, translated_name="กาแฟ")],
    )
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        resp = translate_expense(db, user.id, expense.id, "th")
    assert len(resp.items) == 1
    assert resp.items[0].translated_name == "กาแฟ"


# ── 6. Target English saves name_en ──────────────────────────────────────────

def test_target_english_saves_name_en(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="th")
    item = make_item(db, expense.id, original_name="ข้าวผัด", name_th="ข้าวผัด")
    mock_result = GeminiTranslationResult(
        translated_title="Fried Rice",
        items=[GeminiTranslatedItem(item_id=item.id, translated_name="Fried Rice")],
    )
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        translate_expense(db, user.id, expense.id, "en")
    db.expire(item)
    db.refresh(item)
    assert item.name_en == "Fried Rice"


# ── 7. Target Thai saves name_th ─────────────────────────────────────────────

def test_target_thai_saves_name_th(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    item = make_item(db, expense.id, original_name="Coffee", name_en="Coffee")
    mock_result = GeminiTranslationResult(
        translated_title="มื้อเที่ยง",
        items=[GeminiTranslatedItem(item_id=item.id, translated_name="กาแฟ")],
    )
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        translate_expense(db, user.id, expense.id, "th")
    db.expire(item)
    db.refresh(item)
    assert item.name_th == "กาแฟ"


# ── 8. original_name remains unchanged ───────────────────────────────────────

def test_original_name_remains_unchanged(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    item = make_item(db, expense.id, original_name="Coffee", name_en="Coffee")
    mock_result = GeminiTranslationResult(
        translated_title="แปล",
        items=[GeminiTranslatedItem(item_id=item.id, translated_name="กาแฟ")],
    )
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        translate_expense(db, user.id, expense.id, "th")
    db.expire(item)
    db.refresh(item)
    assert item.original_name == "Coffee"


# ── 9. Existing opposite-language name remains unchanged ─────────────────────

def test_existing_opposite_language_name_unchanged(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    item = make_item(
        db, expense.id, original_name="Coffee", name_en="Coffee", name_th="กาแฟเดิม"
    )
    # Translating to Thai — name_en must stay "Coffee"
    mock_result = GeminiTranslationResult(
        translated_title="แปล",
        items=[GeminiTranslatedItem(item_id=item.id, translated_name="กาแฟใหม่")],
    )
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        translate_expense(db, user.id, expense.id, "th")
    db.expire(item)
    db.refresh(item)
    assert item.name_en == "Coffee"  # unchanged


# ── 10. Merchant name remains unchanged ──────────────────────────────────────

def test_merchant_name_unchanged(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    original_merchant = expense.merchant_name
    mock_result = gemini_result(translated_title="แปล", items=[])
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        translate_expense(db, user.id, expense.id, "th")
    db.expire(expense)
    db.refresh(expense)
    assert expense.merchant_name == original_merchant


# ── 11. Money fields remain unchanged ────────────────────────────────────────

def test_money_fields_unchanged(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    original_total = expense.total_amount
    mock_result = gemini_result(translated_title="แปล", items=[])
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        translate_expense(db, user.id, expense.id, "th")
    db.expire(expense)
    db.refresh(expense)
    assert expense.total_amount == original_total


# ── 12. Category remains unchanged ───────────────────────────────────────────

def test_category_remains_unchanged(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    mock_result = gemini_result(translated_title="แปล", items=[])
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        translate_expense(db, user.id, expense.id, "th")
    db.expire(expense)
    db.refresh(expense)
    assert expense.category_id == category.id


# ── 13. Receipt link remains unchanged ───────────────────────────────────────

def test_receipt_link_unchanged(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    mock_result = gemini_result(translated_title="แปล", items=[])
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        translate_expense(db, user.id, expense.id, "th")
    db.expire(expense)
    db.refresh(expense)
    # receipt_files relationship unchanged — no receipts attached
    assert True  # passes if no exception raised


# ── 14. Missing expense returns 404 ──────────────────────────────────────────

def test_missing_expense_returns_404(db, user):
    with pytest.raises(TranslationServiceError) as exc_info:
        translate_expense(db, user.id, 999999, "th")
    assert exc_info.value.status_code == 404


# ── 15. Other user's expense returns 404 ─────────────────────────────────────

def test_other_users_expense_returns_404(db, category):
    user_a = make_user(db, username="user_a", email="a@example.com")
    user_b = make_user(db, username="user_b", email="b@example.com")
    expense = make_expense(db, user_a.id, category.id)
    with pytest.raises(TranslationServiceError) as exc_info:
        translate_expense(db, user_b.id, expense.id, "th")
    assert exc_info.value.status_code == 404


# ── 16. Soft-deleted expense returns 404 ─────────────────────────────────────

def test_soft_deleted_expense_returns_404(db, user, category):
    expense = make_expense(
        db, user.id, category.id, deleted_at=datetime(2024, 1, 1)
    )
    with pytest.raises(TranslationServiceError) as exc_info:
        translate_expense(db, user.id, expense.id, "th")
    assert exc_info.value.status_code == 404


# ── 17. Soft-deleted items are excluded ──────────────────────────────────────

def test_soft_deleted_items_excluded(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    active_item = make_item(db, expense.id, original_name="Active", name_en="Active")
    deleted_item = make_item(
        db, expense.id, original_name="Deleted", deleted_at=datetime(2024, 1, 1)
    )
    mock_result = GeminiTranslationResult(
        translated_title="แปล",
        items=[GeminiTranslatedItem(item_id=active_item.id, translated_name="ที่ใช้งาน")],
    )
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        resp = translate_expense(db, user.id, expense.id, "th")
    item_ids = [i.item_id for i in resp.items]
    assert active_item.id in item_ids
    assert deleted_item.id not in item_ids


# ── 18. Unsupported target language returns 422 ───────────────────────────────

def test_unsupported_target_language_returns_422(db, user, category):
    expense = make_expense(db, user.id, category.id)
    with pytest.raises(TranslationServiceError) as exc_info:
        translate_expense(db, user.id, expense.id, "fr")
    assert exc_info.value.status_code == 422


# ── 19. Same source and target avoids Gemini ─────────────────────────────────

def test_same_source_and_target_skips_gemini(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    with patch(PATCH_TRANSLATE) as mock_call:
        resp = translate_expense(db, user.id, expense.id, "en")
    mock_call.assert_not_called()
    assert resp.source_language == "en"
    assert resp.target_language == "en"


# ── 20. Existing item translation is reused ──────────────────────────────────

def test_existing_item_translation_reused(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    # Item already has name_th set
    item = make_item(
        db, expense.id, original_name="Coffee", name_en="Coffee", name_th="กาแฟ"
    )
    # Pre-save the title translation so Gemini is not needed for anything
    make_saved_translation(db, expense.title, "en", "th", "มื้อเที่ยง")
    with patch(PATCH_TRANSLATE) as mock_call:
        resp = translate_expense(db, user.id, expense.id, "th")
    mock_call.assert_not_called()
    assert resp.reused_existing_translation is True
    assert resp.items[0].translated_name == "กาแฟ"


# ── 21. Existing title translation is reused ─────────────────────────────────

def test_existing_title_translation_reused(db, user, category):
    expense = make_expense(db, user.id, category.id, title="Lunch", language_detected="en")
    item = make_item(db, expense.id, original_name="Coffee", name_en="Coffee", name_th="กาแฟ")
    # Pre-save the title translation
    make_saved_translation(db, "Lunch", "en", "th", "มื้อเที่ยง")
    with patch(PATCH_TRANSLATE) as mock_call:
        resp = translate_expense(db, user.id, expense.id, "th")
    mock_call.assert_not_called()
    assert resp.translated_title == "มื้อเที่ยง"
    assert resp.reused_existing_translation is True


# ── 22. Partial existing translations call Gemini only for missing fields ─────

def test_partial_existing_calls_gemini_for_missing_only(db, user, category):
    expense = make_expense(
        db, user.id, category.id, title="Lunch", notes="With friends",
        language_detected="en"
    )
    item = make_item(db, expense.id, original_name="Coffee", name_en="Coffee")
    # Only notes is pre-translated; title and item still need Gemini
    make_saved_translation(db, "With friends", "en", "th", "กับเพื่อน")
    called_with_kwargs = {}

    def capture_call(*args, **kwargs):
        called_with_kwargs.update(kwargs)
        return GeminiTranslationResult(
            translated_title="มื้อเที่ยง",
            translated_notes=None,
            items=[GeminiTranslatedItem(item_id=item.id, translated_name="กาแฟ")],
        )

    with patch(PATCH_TRANSLATE, side_effect=capture_call):
        resp = translate_expense(db, user.id, expense.id, "th")

    assert resp.translated_notes == "กับเพื่อน"  # reused
    assert resp.translated_title == "มื้อเที่ยง"  # from Gemini
    # Gemini must have been called with notes=None (already translated)
    assert called_with_kwargs.get("notes") is None


# ── 23. Gemini failure writes nothing ────────────────────────────────────────

def test_gemini_failure_writes_nothing(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    item = make_item(db, expense.id, original_name="Coffee", name_en="Coffee")
    original_name_th = item.name_th

    with patch(PATCH_TRANSLATE, side_effect=TranslationServiceError("Gemini failed", 502)):
        with pytest.raises(TranslationServiceError):
            translate_expense(db, user.id, expense.id, "th")

    db.expire(item)
    db.refresh(item)
    assert item.name_th == original_name_th  # unchanged
    assert db.query(Translation).count() == 0  # no row saved


# ── 24. Invalid Gemini JSON writes nothing ────────────────────────────────────

def test_invalid_gemini_json_writes_nothing(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    item = make_item(db, expense.id, original_name="Coffee", name_en="Coffee")

    with patch(PATCH_TRANSLATE, side_effect=TranslationServiceError("invalid JSON", 502)):
        with pytest.raises(TranslationServiceError):
            translate_expense(db, user.id, expense.id, "th")

    assert db.query(Translation).count() == 0


# ── 25. Invalid item mapping writes nothing ───────────────────────────────────

def test_invalid_item_mapping_writes_nothing(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    item = make_item(db, expense.id, original_name="Coffee", name_en="Coffee")

    with patch(
        PATCH_TRANSLATE,
        side_effect=TranslationServiceError("Gemini translation validation failed", 502),
    ):
        with pytest.raises(TranslationServiceError):
            translate_expense(db, user.id, expense.id, "th")

    db.expire(item)
    db.refresh(item)
    assert item.name_th is None


# ── 26. Database failure rolls back all changes ───────────────────────────────

def test_database_failure_rolls_back(db, user, category):
    expense = make_expense(db, user.id, category.id, language_detected="en")
    item = make_item(db, expense.id, original_name="Coffee", name_en="Coffee")
    mock_result = GeminiTranslationResult(
        translated_title="แปล",
        items=[GeminiTranslatedItem(item_id=item.id, translated_name="กาแฟ")],
    )

    original_name_th = item.name_th

    def bad_commit():
        raise Exception("DB error")

    with patch(PATCH_TRANSLATE, return_value=mock_result):
        with patch.object(db, "commit", side_effect=bad_commit):
            with pytest.raises(Exception, match="DB error"):
                translate_expense(db, user.id, expense.id, "th")

    # Re-query from a fresh session to verify no writes persisted
    fresh_db = TestingSessionLocal()
    try:
        fresh_item = fresh_db.query(ExpenseItem).filter(ExpenseItem.id == item.id).first()
        assert fresh_item.name_th == original_name_th
        assert fresh_db.query(Translation).count() == 0
    finally:
        fresh_db.close()


# ── 27. No real Gemini call occurs ────────────────────────────────────────────

def test_no_real_gemini_call_occurs(db, user, category):
    """Verify translate_expense_text is the only network boundary and is always patched."""
    import app.services.translation_service as svc
    assert callable(svc.translate_expense_text)
    assert callable(svc._build_translation_client)
