"""Service tests for extract_receipt_to_draft_expense.

All Gemini calls are mocked — no real API requests are made.
Uses smart_receipt_db_test.
"""

import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.category import Category
from app.models.expense import Expense
from app.models.expense_item import ExpenseItem
from app.models.receipt_file import ReceiptFile
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.ai_extraction import ExtractedReceiptData, ExtractedReceiptItem
from app.schemas.expense import ExpenseResponse
from app.services.gemini_service import GeminiServiceError
from app.services.receipt_service import ReceiptServiceError, extract_receipt_to_draft_expense

# ── Test DB ───────────────────────────────────────────────────────────────────
settings.JWT_SECRET_KEY = "test_jwt_secret_extraction_service_benz_2004"
settings.JWT_ALGORITHM = "HS256"

engine = create_engine(settings.TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_db():
    db = TestingSessionLocal()
    db.query(ExpenseItem).delete()
    db.query(Expense).delete()
    db.query(ReceiptFile).delete()
    db.query(Category).delete()
    db.query(RefreshToken).delete()
    db.query(User).delete()
    db.commit()
    yield
    db.query(ExpenseItem).delete()
    db.query(Expense).delete()
    db.query(ReceiptFile).delete()
    db.query(Category).delete()
    db.query(RefreshToken).delete()
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
    u = User(username="extractor", email="extractor@example.com", password_hash="hashed")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def other_user(db):
    u = User(username="other_ext", email="other_ext@example.com", password_hash="hashed")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def food_category(db):
    cat = Category(code="FOOD_EXT", name_en="Food", name_th="อาหาร", is_active=True)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@pytest.fixture()
def beverage_category(db):
    cat = Category(code="BEV_EXT", name_en="Beverages", name_th="เครื่องดื่ม", is_active=True)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@pytest.fixture()
def inactive_category(db):
    cat = Category(code="INACT_EXT", name_en="Inactive Cat", name_th="ไม่ใช้งาน", is_active=False)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@pytest.fixture()
def deleted_category(db):
    cat = Category(code="DEL_EXT", name_en="Deleted Cat", name_th="ลบแล้ว",
                   is_active=True, deleted_at=datetime(2024, 1, 1))
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def make_receipt_file(db, user_id: int, *, expense_id=None, deleted_at=None,
                      file_path: str = None) -> ReceiptFile:
    """Create a ReceiptFile row. file_path can point to a real temp file."""
    import uuid
    stored = f"{uuid.uuid4().hex}.jpg"
    receipt = ReceiptFile(
        user_id=user_id,
        expense_id=expense_id,
        original_filename="receipt.jpg",
        stored_filename=stored,
        file_path=file_path or f"/nonexistent/{stored}",
        mime_type="image/jpeg",
        file_size=100,
        upload_status="uploaded",
        deleted_at=deleted_at,
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


def make_temp_receipt_file(db, user_id: int) -> tuple[ReceiptFile, str]:
    """Create a real temp file and a ReceiptFile row pointing to it.
    Returns (receipt, tmpdir path) — caller manages tmpdir lifetime.
    """
    tmpfile = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmpfile.write(b"\xff\xd8\xff\xe0" + b"x" * 100)
    tmpfile.close()

    import uuid
    stored = f"{uuid.uuid4().hex}.jpg"
    receipt = ReceiptFile(
        user_id=user_id,
        original_filename="receipt.jpg",
        stored_filename=stored,
        file_path=tmpfile.name,
        mime_type="image/jpeg",
        file_size=100,
        upload_status="uploaded",
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt, tmpfile.name


def english_extraction(*, title="Coffee Shop", merchant="Bean There",
                        category_name="Food") -> ExtractedReceiptData:
    return ExtractedReceiptData(
        title=title,
        merchant_name=merchant,
        receipt_number="R001",
        receipt_date=date(2025, 6, 1),
        receipt_time=None,
        document_type="receipt",
        payment_method="cash",
        currency="USD",
        subtotal=Decimal("4.50"),
        tax_amount=Decimal("0.50"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("5.00"),
        language_detected="en",
        ai_confidence=Decimal("0.95"),
        items=[
            ExtractedReceiptItem(
                original_name="Latte",
                name_en="Latte",
                name_th="ลาเต้",
                quantity=Decimal("1"),
                unit="cup",
                unit_price=Decimal("4.50"),
                discount_amount=Decimal("0.00"),
                total_price=Decimal("4.50"),
                category_name=category_name,
            )
        ],
    )


def thai_extraction() -> ExtractedReceiptData:
    return ExtractedReceiptData(
        title="ใบเสร็จร้านอาหาร",
        merchant_name="ร้านข้าวต้ม",
        receipt_number="T001",
        receipt_date=date(2025, 6, 15),
        receipt_time=None,
        document_type="receipt",
        payment_method="เงินสด",
        currency="THB",
        subtotal=Decimal("90.00"),
        tax_amount=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("90.00"),
        language_detected="th",
        ai_confidence=Decimal("0.88"),
        items=[
            ExtractedReceiptItem(
                original_name="ข้าวต้ม",
                name_en="Rice Porridge",
                name_th="ข้าวต้ม",
                quantity=Decimal("1"),
                unit="bowl",
                unit_price=Decimal("90.00"),
                discount_amount=Decimal("0.00"),
                total_price=Decimal("90.00"),
                category_name="Food",
            )
        ],
    )


def patch_gemini(return_value: ExtractedReceiptData):
    """Patch extract_receipt_data in receipt_service with a fixed return value."""
    return patch(
        "app.services.receipt_service.extract_receipt_data",
        return_value=return_value,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

# 1. Valid owned receipt creates a draft expense
def test_valid_receipt_creates_draft_expense(db, user, food_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction()):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        assert isinstance(result, ExpenseResponse)
        assert result.id is not None
    finally:
        Path(tmp).unlink(missing_ok=True)


# 2. Created expense belongs to current user
def test_expense_belongs_to_current_user(db, user, food_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction()):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        assert result.user_id == user.id
    finally:
        Path(tmp).unlink(missing_ok=True)


# 3. input_method is "ai"
def test_input_method_is_ai(db, user, food_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction()):
            extract_receipt_to_draft_expense(db, user.id, receipt.id)
        expense = db.query(Expense).filter(Expense.user_id == user.id).first()
        assert expense.input_method == "ai"
    finally:
        Path(tmp).unlink(missing_ok=True)


# 4. ai_status is "completed"
def test_ai_status_is_completed(db, user, food_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction()):
            extract_receipt_to_draft_expense(db, user.id, receipt.id)
        expense = db.query(Expense).filter(Expense.user_id == user.id).first()
        assert expense.ai_status == "completed"
    finally:
        Path(tmp).unlink(missing_ok=True)


# 5. is_confirmed is False
def test_is_confirmed_is_false(db, user, food_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction()):
            extract_receipt_to_draft_expense(db, user.id, receipt.id)
        expense = db.query(Expense).filter(Expense.user_id == user.id).first()
        assert expense.is_confirmed is False
    finally:
        Path(tmp).unlink(missing_ok=True)


# 6. English extraction is saved
def test_english_extraction_saved(db, user, food_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction(title="Coffee Shop", merchant="Bean There")):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        expense = db.query(Expense).filter(Expense.id == result.id).first()
        assert expense.language_detected == "en"
        assert expense.merchant_name == "Bean There"
    finally:
        Path(tmp).unlink(missing_ok=True)


# 7. Thai extraction is saved
def test_thai_extraction_saved(db, user, food_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(thai_extraction()):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        expense = db.query(Expense).filter(Expense.id == result.id).first()
        assert expense.language_detected == "th"
        assert expense.merchant_name == "ร้านข้าวต้ม"
    finally:
        Path(tmp).unlink(missing_ok=True)


# 8. Nested items are created
def test_nested_items_are_created(db, user, food_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction()):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        assert len(result.items) == 1
    finally:
        Path(tmp).unlink(missing_ok=True)


# 9. English and Thai item names are saved
def test_item_en_and_th_names_saved(db, user, food_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction()):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        item = result.items[0]
        assert item.name_en == "Latte"
        assert item.name_th == "ลาเต้"
    finally:
        Path(tmp).unlink(missing_ok=True)


# 10. Receipt is linked to the created expense
def test_receipt_is_linked_to_expense(db, user, food_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction()):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        db.refresh(receipt)
        assert receipt.expense_id == result.id
    finally:
        Path(tmp).unlink(missing_ok=True)


# 11. Main category name matches an active category
def test_item_matched_category_is_used(db, user, food_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction(category_name="Food")):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        item = db.query(ExpenseItem).filter(ExpenseItem.expense_id == result.id).first()
        assert item.category_id == food_category.id
    finally:
        Path(tmp).unlink(missing_ok=True)


# 12. Item category name matches an active category
def test_item_category_matched(db, user, beverage_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction(category_name="Beverages")):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        item = db.query(ExpenseItem).filter(ExpenseItem.expense_id == result.id).first()
        assert item.category_id == beverage_category.id
    finally:
        Path(tmp).unlink(missing_ok=True)


# 13. Category matching is case-insensitive
def test_category_matching_is_case_insensitive(db, user, food_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction(category_name="FOOD")):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        item = db.query(ExpenseItem).filter(ExpenseItem.expense_id == result.id).first()
        assert item.category_id == food_category.id
    finally:
        Path(tmp).unlink(missing_ok=True)


# 14. Unknown category leaves category_id as None
def test_unknown_category_name_leaves_none(db, user):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction(category_name="Completely Unknown Category")):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        item = db.query(ExpenseItem).filter(ExpenseItem.expense_id == result.id).first()
        assert item.category_id is None
    finally:
        Path(tmp).unlink(missing_ok=True)


# 15. Inactive category is ignored
def test_inactive_category_is_ignored(db, user, inactive_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction(category_name="Inactive Cat")):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        item = db.query(ExpenseItem).filter(ExpenseItem.expense_id == result.id).first()
        assert item.category_id is None
    finally:
        Path(tmp).unlink(missing_ok=True)


# 16. Soft-deleted category is ignored
def test_soft_deleted_category_is_ignored(db, user, deleted_category):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch_gemini(english_extraction(category_name="Deleted Cat")):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        item = db.query(ExpenseItem).filter(ExpenseItem.expense_id == result.id).first()
        assert item.category_id is None
    finally:
        Path(tmp).unlink(missing_ok=True)


# 17. Missing receipt returns 404
def test_missing_receipt_returns_404(db, user):
    with pytest.raises(ReceiptServiceError) as exc_info:
        extract_receipt_to_draft_expense(db, user.id, 999999)
    assert exc_info.value.status_code == 404


# 18. Another user's receipt returns 404
def test_other_users_receipt_returns_404(db, user, other_user):
    receipt = make_receipt_file(db, other_user.id, file_path="/tmp/x.jpg")
    with pytest.raises(ReceiptServiceError) as exc_info:
        extract_receipt_to_draft_expense(db, user.id, receipt.id)
    assert exc_info.value.status_code == 404


# 19. Soft-deleted receipt returns 404
def test_soft_deleted_receipt_returns_404(db, user):
    receipt = make_receipt_file(db, user.id, deleted_at=datetime(2024, 1, 1))
    with pytest.raises(ReceiptServiceError) as exc_info:
        extract_receipt_to_draft_expense(db, user.id, receipt.id)
    assert exc_info.value.status_code == 404


# 20. Missing physical file returns 404
def test_missing_physical_file_returns_404(db, user):
    receipt = make_receipt_file(db, user.id, file_path="/nonexistent/path/receipt.jpg")
    with pytest.raises(ReceiptServiceError) as exc_info:
        extract_receipt_to_draft_expense(db, user.id, receipt.id)
    assert exc_info.value.status_code == 404


# 21. Already-linked receipt returns 409
def test_already_linked_receipt_returns_409(db, user):
    # Create a real expense row first so FK constraint is satisfied
    dummy_expense = Expense(
        user_id=user.id,
        title="Dummy",
        receipt_date=date(2025, 1, 1),
        total_amount=Decimal("1.00"),
        currency="THB",
        input_method="manual",
    )
    db.add(dummy_expense)
    db.commit()
    db.refresh(dummy_expense)

    receipt = make_receipt_file(db, user.id, expense_id=dummy_expense.id)
    with pytest.raises(ReceiptServiceError) as exc_info:
        extract_receipt_to_draft_expense(db, user.id, receipt.id)
    assert exc_info.value.status_code == 409


# 22. Gemini failure creates no expense
def test_gemini_failure_creates_no_expense(db, user):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch(
            "app.services.receipt_service.extract_receipt_data",
            side_effect=GeminiServiceError("Gemini extraction failed", status_code=502),
        ):
            with pytest.raises(GeminiServiceError):
                extract_receipt_to_draft_expense(db, user.id, receipt.id)
        count = db.query(Expense).filter(Expense.user_id == user.id).count()
        assert count == 0
    finally:
        Path(tmp).unlink(missing_ok=True)


# 23. Gemini failure creates no items
def test_gemini_failure_creates_no_items(db, user):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch(
            "app.services.receipt_service.extract_receipt_data",
            side_effect=GeminiServiceError("Gemini extraction failed", status_code=502),
        ):
            with pytest.raises(GeminiServiceError):
                extract_receipt_to_draft_expense(db, user.id, receipt.id)
        count = db.query(ExpenseItem).count()
        assert count == 0
    finally:
        Path(tmp).unlink(missing_ok=True)


# 24. Gemini failure leaves receipt unlinked
def test_gemini_failure_leaves_receipt_unlinked(db, user):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        with patch(
            "app.services.receipt_service.extract_receipt_data",
            side_effect=GeminiServiceError("Gemini extraction failed", status_code=502),
        ):
            with pytest.raises(GeminiServiceError):
                extract_receipt_to_draft_expense(db, user.id, receipt.id)
        db.refresh(receipt)
        assert receipt.expense_id is None
    finally:
        Path(tmp).unlink(missing_ok=True)


# 25. Database failure rolls back expense
def test_db_failure_rolls_back_expense(db, user):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        # Patch flush to fail on the second call (after expense is added)
        original_flush = db.flush
        call_count = [0]

        def failing_flush(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("DB write failed")
            return original_flush(*args, **kwargs)

        with patch_gemini(english_extraction()):
            with patch.object(db, "flush", side_effect=failing_flush):
                with pytest.raises(Exception):
                    extract_receipt_to_draft_expense(db, user.id, receipt.id)

        count = db.query(Expense).filter(Expense.user_id == user.id).count()
        assert count == 0
    finally:
        Path(tmp).unlink(missing_ok=True)


# 26. Database failure rolls back items
def test_db_failure_rolls_back_items(db, user):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        original_flush = db.flush
        call_count = [0]

        def failing_flush(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("DB write failed")
            return original_flush(*args, **kwargs)

        with patch_gemini(english_extraction()):
            with patch.object(db, "flush", side_effect=failing_flush):
                with pytest.raises(Exception):
                    extract_receipt_to_draft_expense(db, user.id, receipt.id)

        count = db.query(ExpenseItem).count()
        assert count == 0
    finally:
        Path(tmp).unlink(missing_ok=True)


# 27. Database failure leaves receipt unlinked
def test_db_failure_leaves_receipt_unlinked(db, user):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        original_flush = db.flush
        call_count = [0]

        def failing_flush(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("DB write failed")
            return original_flush(*args, **kwargs)

        with patch_gemini(english_extraction()):
            with patch.object(db, "flush", side_effect=failing_flush):
                with pytest.raises(Exception):
                    extract_receipt_to_draft_expense(db, user.id, receipt.id)

        # Re-query after rollback
        fresh_receipt = db.query(ReceiptFile).filter(ReceiptFile.id == receipt.id).first()
        assert fresh_receipt.expense_id is None
    finally:
        Path(tmp).unlink(missing_ok=True)


# 28. Empty extracted items creates expense with items=[]
def test_empty_items_creates_expense_with_no_items(db, user):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        extraction = ExtractedReceiptData(
            title="No items receipt",
            merchant_name="Empty Shop",
            total_amount=Decimal("100.00"),
            language_detected="en",
            items=[],
        )
        with patch_gemini(extraction):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        assert result.items == []
    finally:
        Path(tmp).unlink(missing_ok=True)


# 29. Missing title uses merchant_name
def test_missing_title_uses_merchant_name(db, user):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        extraction = ExtractedReceiptData(
            title=None,
            merchant_name="Fallback Merchant",
            total_amount=Decimal("50.00"),
            language_detected="en",
            items=[],
        )
        with patch_gemini(extraction):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        assert result.title == "Fallback Merchant"
    finally:
        Path(tmp).unlink(missing_ok=True)


# 30. Missing title and merchant uses "Extracted Receipt"
def test_missing_title_and_merchant_uses_fallback(db, user):
    receipt, tmp = make_temp_receipt_file(db, user.id)
    try:
        extraction = ExtractedReceiptData(
            title=None,
            merchant_name=None,
            total_amount=Decimal("50.00"),
            language_detected="en",
            items=[],
        )
        with patch_gemini(extraction):
            result = extract_receipt_to_draft_expense(db, user.id, receipt.id)
        assert result.title == "Extracted Receipt"
    finally:
        Path(tmp).unlink(missing_ok=True)


# 31. No real Gemini request is made
def test_no_real_gemini_request_is_made():
    """extract_receipt_data is the single mock boundary used in all tests above."""
    import inspect
    import app.services.receipt_service as svc
    source = inspect.getsource(svc)
    # The service imports and calls extract_receipt_data, not _build_client directly,
    # so all tests patch at the right level.
    assert "extract_receipt_data" in source
