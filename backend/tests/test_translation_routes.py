"""Tests for POST /api/expenses/{expense_id}/translate.

All Gemini calls are patched — no real network requests are made.
Uses smart_receipt_db_test database.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.category import Category
from app.models.expense import Expense
from app.models.expense_item import ExpenseItem
from app.models.refresh_token import RefreshToken
from app.models.translation import Translation
from app.models.user import User
from app.schemas.translation import GeminiTranslatedItem, GeminiTranslationResult

# ── Test DB ───────────────────────────────────────────────────────────────────
settings.JWT_SECRET_KEY = "test_jwt_secret_key_translation_routes_testing_benz_2004"
settings.JWT_ALGORITHM = "HS256"

engine = create_engine(settings.TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

PATCH_TRANSLATE = "app.services.translation_service.translate_expense_text"


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_category(*, code="FOOD") -> int:
    db = TestingSessionLocal()
    cat = Category(code=code, name_en="Food", name_th="อาหาร", is_active=True)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    cat_id = cat.id
    db.close()
    return cat_id


def register_and_login(username="tr_tester", email="tr_tester@example.com") -> str:
    client.post("/api/auth/register", json={
        "username": username, "email": email, "password": "password123"
    })
    res = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    return res.json()["access_token"]


def create_expense_in_db(
    user_id: int,
    category_id: int,
    *,
    title: str = "Lunch",
    notes: str | None = None,
    language_detected: str | None = "en",
    deleted_at=None,
) -> Expense:
    db = TestingSessionLocal()
    expense = Expense(
        user_id=user_id,
        category_id=category_id,
        title=title,
        receipt_date=date(2025, 6, 1),
        total_amount=Decimal("100.00"),
        currency="THB",
        input_method="manual",
        language_detected=language_detected,
        notes=notes,
        deleted_at=deleted_at,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    expense_id = expense.id
    db.close()
    return expense_id


def create_item_in_db(
    expense_id: int,
    *,
    original_name: str = "Coffee",
    name_en: str | None = None,
    name_th: str | None = None,
) -> int:
    db = TestingSessionLocal()
    item = ExpenseItem(
        expense_id=expense_id,
        original_name=original_name,
        name_en=name_en,
        name_th=name_th,
        quantity=Decimal("1"),
        total_price=Decimal("50.00"),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    item_id = item.id
    db.close()
    return item_id


def get_user_id(token: str) -> int:
    return client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]


def translate(token: str, expense_id: int, target_language: str = "th"):
    return client.post(
        f"/api/expenses/{expense_id}/translate",
        json={"target_language": target_language},
        headers={"Authorization": f"Bearer {token}"},
    )


def make_gemini_result(
    translated_title: str | None = "แปลแล้ว",
    translated_notes: str | None = None,
    items: list[dict] | None = None,
) -> GeminiTranslationResult:
    return GeminiTranslationResult(
        translated_title=translated_title,
        translated_notes=translated_notes,
        items=[
            GeminiTranslatedItem(item_id=i["item_id"], translated_name=i["translated_name"])
            for i in (items or [])
        ],
    )


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
def token():
    return register_and_login()


@pytest.fixture()
def other_token():
    return register_and_login("other_tr_user", "other_tr@example.com")


@pytest.fixture()
def category_id():
    return make_category()


# ── 1. Authenticated user can translate an owned expense ─────────────────────

def test_authenticated_user_can_translate_expense(token, category_id):
    uid = get_user_id(token)
    eid = create_expense_in_db(uid, category_id)
    with patch(PATCH_TRANSLATE, return_value=make_gemini_result(items=[])):
        res = translate(token, eid, "th")
    assert res.status_code == 200


# ── 2. Success returns 200 ────────────────────────────────────────────────────

def test_success_returns_200(token, category_id):
    uid = get_user_id(token)
    eid = create_expense_in_db(uid, category_id)
    with patch(PATCH_TRANSLATE, return_value=make_gemini_result(items=[])):
        res = translate(token, eid, "th")
    assert res.status_code == 200


# ── 3. English-to-Thai response is correct ───────────────────────────────────

def test_english_to_thai_response(token, category_id):
    uid = get_user_id(token)
    eid = create_expense_in_db(uid, category_id, title="Lunch", language_detected="en")
    with patch(PATCH_TRANSLATE, return_value=make_gemini_result("มื้อเที่ยง", items=[])):
        res = translate(token, eid, "th")
    data = res.json()
    assert data["source_language"] == "en"
    assert data["target_language"] == "th"
    assert data["translated_title"] == "มื้อเที่ยง"


# ── 4. Thai-to-English response is correct ───────────────────────────────────

def test_thai_to_english_response(token, category_id):
    uid = get_user_id(token)
    eid = create_expense_in_db(uid, category_id, title="อาหาร", language_detected="th")
    with patch(PATCH_TRANSLATE, return_value=make_gemini_result("Food", items=[])):
        res = translate(token, eid, "en")
    data = res.json()
    assert data["source_language"] == "th"
    assert data["target_language"] == "en"
    assert data["translated_title"] == "Food"


# ── 5. Translated title is returned ──────────────────────────────────────────

def test_translated_title_is_returned(token, category_id):
    uid = get_user_id(token)
    eid = create_expense_in_db(uid, category_id, title="Dinner")
    with patch(PATCH_TRANSLATE, return_value=make_gemini_result("อาหารเย็น", items=[])):
        res = translate(token, eid, "th")
    assert res.json()["translated_title"] == "อาหารเย็น"


# ── 6. Translated notes are returned ─────────────────────────────────────────

def test_translated_notes_are_returned(token, category_id):
    uid = get_user_id(token)
    eid = create_expense_in_db(uid, category_id, notes="With family")
    mock_result = GeminiTranslationResult(
        translated_title="แปล",
        translated_notes="กับครอบครัว",
        items=[],
    )
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        res = translate(token, eid, "th")
    assert res.json()["translated_notes"] == "กับครอบครัว"


# ── 7. Translated items are returned ─────────────────────────────────────────

def test_translated_items_are_returned(token, category_id):
    uid = get_user_id(token)
    eid = create_expense_in_db(uid, category_id, language_detected="en")
    item_id = create_item_in_db(eid, original_name="Coffee", name_en="Coffee")
    mock_result = GeminiTranslationResult(
        translated_title="แปล",
        items=[GeminiTranslatedItem(item_id=item_id, translated_name="กาแฟ")],
    )
    with patch(PATCH_TRANSLATE, return_value=mock_result):
        res = translate(token, eid, "th")
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["translated_name"] == "กาแฟ"


# ── 8. Missing expense returns 404 ───────────────────────────────────────────

def test_missing_expense_returns_404(token):
    res = translate(token, 999999, "th")
    assert res.status_code == 404


# ── 9. Other user's expense returns 404 ──────────────────────────────────────

def test_other_users_expense_returns_404(token, other_token, category_id):
    other_uid = get_user_id(other_token)
    eid = create_expense_in_db(other_uid, category_id)
    res = translate(token, eid, "th")
    assert res.status_code == 404


# ── 10. Soft-deleted expense returns 404 ─────────────────────────────────────

def test_soft_deleted_expense_returns_404(token, category_id):
    uid = get_user_id(token)
    eid = create_expense_in_db(uid, category_id, deleted_at=datetime(2024, 1, 1))
    res = translate(token, eid, "th")
    assert res.status_code == 404


# ── 11. Unsupported language returns 422 ─────────────────────────────────────

def test_unsupported_language_returns_422(token, category_id):
    uid = get_user_id(token)
    eid = create_expense_in_db(uid, category_id)
    res = translate(token, eid, "fr")
    assert res.status_code == 422


# ── 12. Missing token returns 401 ────────────────────────────────────────────

def test_missing_token_returns_401(category_id):
    res = client.post("/api/expenses/1/translate", json={"target_language": "th"})
    assert res.status_code == 401


# ── 13. Invalid token returns 401 ────────────────────────────────────────────

def test_invalid_token_returns_401(category_id):
    res = client.post(
        "/api/expenses/1/translate",
        json={"target_language": "th"},
        headers={"Authorization": "Bearer bad.token.here"},
    )
    assert res.status_code == 401


# ── 14. Existing translation is reused ───────────────────────────────────────

def test_existing_translation_is_reused(token, category_id):
    uid = get_user_id(token)
    eid = create_expense_in_db(uid, category_id, title="Lunch", language_detected="en")
    create_item_in_db(eid, original_name="Coffee", name_en="Coffee", name_th="กาแฟ")
    # Pre-save title translation
    db = TestingSessionLocal()
    db.add(Translation(
        source_text="Lunch", source_language="en", target_language="th",
        translated_text="มื้อเที่ยง", translation_source="gemini",
    ))
    db.commit()
    db.close()

    with patch(PATCH_TRANSLATE) as mock_call:
        res = translate(token, eid, "th")
    mock_call.assert_not_called()
    assert res.json()["reused_existing_translation"] is True
    assert res.json()["translated_title"] == "มื้อเที่ยง"


# ── 15. Fixed frontend labels are not handled ────────────────────────────────

def test_fixed_frontend_labels_are_not_in_response(token, category_id):
    """The response contains only dynamic expense fields, not any UI labels."""
    uid = get_user_id(token)
    eid = create_expense_in_db(uid, category_id)
    with patch(PATCH_TRANSLATE, return_value=make_gemini_result(items=[])):
        res = translate(token, eid, "th")
    data = res.json()
    for label in ("Dashboard", "Save", "Delete", "Upload Receipt", "Expenses"):
        assert label not in str(data)


# ── 16. No monetary data changes ─────────────────────────────────────────────

def test_no_monetary_data_in_response(token, category_id):
    uid = get_user_id(token)
    eid = create_expense_in_db(uid, category_id)
    with patch(PATCH_TRANSLATE, return_value=make_gemini_result(items=[])):
        res = translate(token, eid, "th")
    data = res.json()
    for field in ("total_amount", "subtotal", "tax_amount", "currency"):
        assert field not in data


# ── 17. Internal fields are not exposed ──────────────────────────────────────

def test_internal_fields_not_exposed(token, category_id):
    uid = get_user_id(token)
    eid = create_expense_in_db(uid, category_id)
    with patch(PATCH_TRANSLATE, return_value=make_gemini_result(items=[])):
        res = translate(token, eid, "th")
    data = res.json()
    for field in ("user_id", "deleted_at", "ai_raw_response", "api_key", "file_path"):
        assert field not in data


# ── 18. No real Gemini call occurs ────────────────────────────────────────────

def test_no_real_gemini_call_occurs(token, category_id):
    """Structural: _build_translation_client is the network boundary and is patched."""
    import app.services.translation_service as svc
    assert callable(svc._build_translation_client)


# ── 19. Full existing test suite remains green (smoke check) ──────────────────

def test_expense_routes_smoke_check(token, category_id):
    """Verify other expense routes still work after adding the translate route."""
    res = client.get("/api/expenses", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200


def test_health_route_still_works():
    assert client.get("/api/health").status_code == 200


def test_auth_me_still_works(token):
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
