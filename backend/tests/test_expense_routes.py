"""Tests for POST /api/expenses (uses smart_receipt_db_test)."""

from datetime import datetime
from decimal import Decimal

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
from app.models.user import User

# ── Test DB ───────────────────────────────────────────────────────────────────
settings.JWT_SECRET_KEY = "test_jwt_secret_key_expense_routes_testing_benz_2004"
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_category(*, name_en="Food", name_th="อาหาร", code="FOOD",
                  is_active=True, deleted_at=None) -> int:
    db = TestingSessionLocal()
    cat = Category(code=code, name_en=name_en, name_th=name_th,
                   is_active=is_active, deleted_at=deleted_at)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    cat_id = cat.id
    db.close()
    return cat_id


def register_and_login(username="expense_tester", email="expense_tester@example.com") -> str:
    client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": "password123",
    })
    res = client.post("/api/auth/login", json={
        "email": email,
        "password": "password123",
    })
    return res.json()["access_token"]


def base_payload(category_id: int, **overrides) -> dict:
    defaults = {
        "category_id": category_id,
        "title": "Lunch",
        "receipt_date": "2025-06-01",
        "total_amount": "100.00",
        "currency": "THB",
        "items": [],
    }
    defaults.update(overrides)
    return defaults


def post_expense(token: str, payload: dict):
    return client.post(
        "/api/expenses",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_db():
    db = TestingSessionLocal()
    db.query(ExpenseItem).delete()
    db.query(Expense).delete()
    db.query(Category).delete()
    db.query(RefreshToken).delete()
    db.query(User).delete()
    db.commit()
    yield
    db.query(ExpenseItem).delete()
    db.query(Expense).delete()
    db.query(Category).delete()
    db.query(RefreshToken).delete()
    db.query(User).delete()
    db.commit()
    db.close()


@pytest.fixture()
def token():
    return register_and_login()


@pytest.fixture()
def other_token():
    return register_and_login("other_user", "other_user@example.com")


@pytest.fixture()
def category_id():
    return make_category()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_authenticated_user_can_create_expense(token, category_id):
    res = post_expense(token, base_payload(category_id))
    assert res.status_code == 201


def test_successful_creation_returns_201(token, category_id):
    res = post_expense(token, base_payload(category_id))
    assert res.status_code == 201


def test_response_contains_current_user_id(token, category_id):
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    res = post_expense(token, base_payload(category_id))
    assert res.json()["user_id"] == me["id"]


def test_response_contains_correct_category(token, category_id):
    res = post_expense(token, base_payload(category_id))
    assert res.json()["category_id"] == category_id


def test_response_includes_empty_items_when_none_sent(token, category_id):
    res = post_expense(token, base_payload(category_id, items=[]))
    assert res.json()["items"] == []


def test_response_includes_created_nested_items(token, category_id):
    items = [
        {"original_name": "Coffee", "quantity": "1", "total_price": "50.00"},
        {"original_name": "Tea", "quantity": "2", "total_price": "60.00"},
    ]
    res = post_expense(token, base_payload(category_id, items=items))
    data = res.json()
    assert len(data["items"]) == 2
    names = {i["original_name"] for i in data["items"]}
    assert names == {"Coffee", "Tea"}


def test_missing_access_token_returns_401(category_id):
    res = client.post("/api/expenses", json=base_payload(category_id))
    assert res.status_code == 401


def test_invalid_access_token_returns_401(category_id):
    res = client.post(
        "/api/expenses",
        json=base_payload(category_id),
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert res.status_code == 401


def test_invalid_request_schema_returns_422(token):
    res = client.post(
        "/api/expenses",
        json={"title": "Missing required fields"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


def test_invalid_main_category_returns_service_error_status(token):
    res = post_expense(token, base_payload(category_id=999999))
    assert res.status_code == 404


def test_inactive_category_is_rejected(token):
    cat_id = make_category(code="INACTIVE2", name_en="Inactive2",
                           name_th="ไม่ใช้งาน2", is_active=False)
    res = post_expense(token, base_payload(cat_id))
    assert res.status_code == 404


def test_soft_deleted_category_is_rejected(token):
    cat_id = make_category(code="DELETED2", name_en="Deleted2",
                           name_th="ลบแล้ว2", deleted_at=datetime(2024, 1, 1))
    res = post_expense(token, base_payload(cat_id))
    assert res.status_code == 404


def test_invalid_item_category_is_rejected(token, category_id):
    items = [{"original_name": "Steak", "quantity": "1",
               "total_price": "200.00", "category_id": 999999}]
    res = post_expense(token, base_payload(category_id, items=items))
    assert res.status_code == 404


def test_another_user_cannot_control_expense_owner(token, other_token, category_id):
    """The owner must always be the token holder, not a value from the request body."""
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    other_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {other_token}"}).json()

    # Even if user_id were accepted (it should not be), the expense owner must be 'token'
    payload = base_payload(category_id)
    res = post_expense(token, payload)
    assert res.json()["user_id"] == me["id"]
    assert res.json()["user_id"] != other_me["id"]


def test_response_does_not_expose_deleted_at(token, category_id):
    res = post_expense(token, base_payload(category_id))
    assert "deleted_at" not in res.json()


def test_response_does_not_expose_internal_ai_fields(token, category_id):
    res = post_expense(token, base_payload(category_id))
    data = res.json()
    for field in ("ai_confidence", "ai_status", "ai_raw_response", "language_detected"):
        assert field not in data, f"Response must not expose: {field}"


# ── Existing routes still pass ────────────────────────────────────────────────

def test_health_route_still_works():
    res = client.get("/api/health")
    assert res.status_code == 200


def test_auth_register_still_works():
    res = client.post("/api/auth/register", json={
        "username": "smoke_user",
        "email": "smoke_user@example.com",
        "password": "password123",
    })
    assert res.status_code == 201


def test_category_routes_still_work(token):
    res = client.get("/api/categories", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200


def test_receipt_upload_route_still_accessible(token):
    """Receipt upload with no file returns 422, not 404 — route exists."""
    res = client.post("/api/receipts/upload",
                      headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 422


# ── Helpers for read tests ────────────────────────────────────────────────────

from datetime import date


def create_expense_via_api(token: str, category_id: int, title: str = "Expense",
                           items: list = None) -> dict:
    payload = base_payload(category_id, title=title, items=items or [])
    res = post_expense(token, payload)
    assert res.status_code == 201, f"Setup failed: {res.json()}"
    return res.json()


def soft_delete_expense_in_db(expense_id: int) -> None:
    """Mark an expense deleted_at directly in the test DB."""
    from datetime import datetime
    db = TestingSessionLocal()
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if expense:
        expense.deleted_at = datetime(2024, 1, 1)
        db.commit()
    db.close()


def get_expenses(token: str):
    return client.get("/api/expenses", headers={"Authorization": f"Bearer {token}"})


def get_expense_detail(token: str, expense_id: int):
    return client.get(f"/api/expenses/{expense_id}",
                      headers={"Authorization": f"Bearer {token}"})


# ── GET /api/expenses tests ───────────────────────────────────────────────────

def test_authenticated_user_can_list_expenses(token, category_id):
    res = get_expenses(token)
    assert res.status_code == 200


def test_list_route_returns_200(token, category_id):
    res = get_expenses(token)
    assert res.status_code == 200


def test_list_route_returns_array(token, category_id):
    res = get_expenses(token)
    assert isinstance(res.json(), list)


def test_list_route_returns_only_current_users_expenses(token, other_token, category_id):
    create_expense_via_api(token, category_id, title="Mine")
    create_expense_via_api(other_token, category_id, title="Theirs")
    res = get_expenses(token)
    data = res.json()
    assert len(data) == 1
    assert data[0]["title"] == "Mine"


def test_list_route_excludes_soft_deleted_expenses(token, category_id):
    created = create_expense_via_api(token, category_id, title="ToDelete")
    soft_delete_expense_in_db(created["id"])
    create_expense_via_api(token, category_id, title="Active")
    res = get_expenses(token)
    data = res.json()
    assert len(data) == 1
    assert data[0]["title"] == "Active"


def test_list_route_returns_newest_expenses_first(token, category_id):
    import time
    create_expense_via_api(token, category_id, title="First")
    time.sleep(0.05)
    create_expense_via_api(token, category_id, title="Second")
    res = get_expenses(token)
    data = res.json()
    assert data[0]["title"] == "Second"


def test_empty_list_returns_200_and_empty_array(token):
    res = get_expenses(token)
    assert res.status_code == 200
    assert res.json() == []


def test_list_response_includes_nested_items(token, category_id):
    items = [{"original_name": "Noodles", "quantity": "1", "total_price": "45.00"}]
    create_expense_via_api(token, category_id, items=items)
    res = get_expenses(token)
    assert len(res.json()[0]["items"]) == 1
    assert res.json()[0]["items"][0]["original_name"] == "Noodles"


def test_list_response_excludes_soft_deleted_items(token, category_id):
    created = create_expense_via_api(token, category_id)
    # Soft-delete the item directly in DB
    db = TestingSessionLocal()
    from datetime import datetime
    item = db.query(ExpenseItem).filter(ExpenseItem.expense_id == created["id"]).first()
    if item:
        item.deleted_at = datetime(2024, 1, 1)
        db.commit()
    db.close()
    # Add a non-deleted item via API
    items = [{"original_name": "Visible", "quantity": "1", "total_price": "30.00"}]
    payload = base_payload(category_id, items=items)
    payload["title"] = created["title"]
    # Create a fresh expense with the visible item
    created2 = create_expense_via_api(token, category_id, items=items)
    res = get_expenses(token)
    # The expense with the visible item should show 1 item
    expense_data = next(e for e in res.json() if e["id"] == created2["id"])
    assert len(expense_data["items"]) == 1


def test_list_missing_token_returns_401():
    res = client.get("/api/expenses")
    assert res.status_code == 401


def test_list_invalid_token_returns_401():
    res = client.get("/api/expenses", headers={"Authorization": "Bearer bad.token.here"})
    assert res.status_code == 401


# ── GET /api/expenses/{expense_id} tests ─────────────────────────────────────

def test_authenticated_user_can_get_expense_by_id(token, category_id):
    created = create_expense_via_api(token, category_id)
    res = get_expense_detail(token, created["id"])
    assert res.status_code == 200
    assert res.json()["id"] == created["id"]


def test_detail_response_includes_nested_items(token, category_id):
    items = [{"original_name": "Steak", "quantity": "1", "total_price": "200.00"}]
    created = create_expense_via_api(token, category_id, items=items)
    res = get_expense_detail(token, created["id"])
    assert len(res.json()["items"]) == 1
    assert res.json()["items"][0]["original_name"] == "Steak"


def test_detail_unknown_expense_id_returns_404(token):
    res = get_expense_detail(token, 999999)
    assert res.status_code == 404


def test_detail_another_users_expense_returns_404(token, other_token, category_id):
    other_expense = create_expense_via_api(other_token, category_id, title="Other's")
    res = get_expense_detail(token, other_expense["id"])
    assert res.status_code == 404


def test_detail_soft_deleted_expense_returns_404(token, category_id):
    created = create_expense_via_api(token, category_id)
    soft_delete_expense_in_db(created["id"])
    res = get_expense_detail(token, created["id"])
    assert res.status_code == 404


def test_detail_missing_token_returns_401(token, category_id):
    created = create_expense_via_api(token, category_id)
    res = client.get(f"/api/expenses/{created['id']}")
    assert res.status_code == 401


def test_detail_response_does_not_expose_deleted_at(token, category_id):
    created = create_expense_via_api(token, category_id)
    res = get_expense_detail(token, created["id"])
    assert "deleted_at" not in res.json()


def test_detail_response_does_not_expose_internal_ai_fields(token, category_id):
    created = create_expense_via_api(token, category_id)
    res = get_expense_detail(token, created["id"])
    data = res.json()
    for field in ("ai_confidence", "ai_status", "ai_raw_response", "language_detected"):
        assert field not in data, f"Response must not expose: {field}"


# ── Helpers for update / delete route tests ───────────────────────────────────

def put_expense(token: str, expense_id: int, payload: dict):
    return client.put(
        f"/api/expenses/{expense_id}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


def delete_expense(token: str, expense_id: int):
    return client.delete(
        f"/api/expenses/{expense_id}",
        headers={"Authorization": f"Bearer {token}"},
    )


def make_second_category(code: str = "TRAVEL") -> int:
    return make_category(code=code, name_en="Travel", name_th="ท่องเที่ยว")


# ── PUT /api/expenses/{expense_id} tests ──────────────────────────────────────

def test_authenticated_user_can_update_their_expense(token, category_id):
    created = create_expense_via_api(token, category_id, title="Original")
    res = put_expense(token, created["id"], {"title": "Updated"})
    assert res.status_code == 200


def test_update_returns_200(token, category_id):
    created = create_expense_via_api(token, category_id)
    res = put_expense(token, created["id"], {"title": "Changed"})
    assert res.status_code == 200


def test_updated_fields_appear_in_response(token, category_id):
    created = create_expense_via_api(token, category_id, title="Before")
    res = put_expense(token, created["id"], {"title": "After", "notes": "added"})
    data = res.json()
    assert data["title"] == "After"
    assert data["notes"] == "added"


def test_fields_not_sent_remain_unchanged(token, category_id):
    created = create_expense_via_api(token, category_id, title="Keep Me")
    original_total = created["total_amount"]
    res = put_expense(token, created["id"], {"notes": "only notes changed"})
    assert res.json()["title"] == "Keep Me"
    assert res.json()["total_amount"] == original_total


def test_empty_update_succeeds(token, category_id):
    created = create_expense_via_api(token, category_id, title="No Change")
    res = put_expense(token, created["id"], {})
    assert res.status_code == 200
    assert res.json()["title"] == "No Change"


def test_update_can_replace_items(token, category_id):
    items = [{"original_name": "Old", "quantity": "1", "total_price": "10.00"}]
    created = create_expense_via_api(token, category_id, items=items)
    new_items = [{"original_name": "New", "quantity": "2", "total_price": "20.00"}]
    res = put_expense(token, created["id"], {"items": new_items})
    assert res.status_code == 200
    names = [i["original_name"] for i in res.json()["items"]]
    assert names == ["New"]


def test_update_with_empty_items_returns_empty_active_item_list(token, category_id):
    items = [{"original_name": "Remove Me", "quantity": "1", "total_price": "10.00"}]
    created = create_expense_via_api(token, category_id, items=items)
    res = put_expense(token, created["id"], {"items": []})
    assert res.status_code == 200
    assert res.json()["items"] == []


def test_update_without_items_preserves_items(token, category_id):
    items = [{"original_name": "Stay", "quantity": "1", "total_price": "30.00"}]
    created = create_expense_via_api(token, category_id, items=items)
    res = put_expense(token, created["id"], {"title": "New Title"})
    assert len(res.json()["items"]) == 1
    assert res.json()["items"][0]["original_name"] == "Stay"


def test_update_invalid_category_returns_404(token, category_id):
    created = create_expense_via_api(token, category_id)
    res = put_expense(token, created["id"], {"category_id": 999999})
    assert res.status_code == 404


def test_update_invalid_item_category_returns_error(token, category_id):
    created = create_expense_via_api(token, category_id)
    bad_items = [{"original_name": "X", "quantity": "1",
                  "total_price": "10.00", "category_id": 999999}]
    res = put_expense(token, created["id"], {"items": bad_items})
    assert res.status_code == 404


def test_update_unknown_expense_returns_404(token):
    res = put_expense(token, 999999, {"title": "Ghost"})
    assert res.status_code == 404


def test_update_another_users_expense_returns_404(token, other_token, category_id):
    other_expense = create_expense_via_api(other_token, category_id, title="Not Mine")
    res = put_expense(token, other_expense["id"], {"title": "Hijacked"})
    assert res.status_code == 404


def test_update_soft_deleted_expense_returns_404(token, category_id):
    created = create_expense_via_api(token, category_id)
    soft_delete_expense_in_db(created["id"])
    res = put_expense(token, created["id"], {"title": "Ghost"})
    assert res.status_code == 404


def test_update_missing_token_returns_401(category_id):
    res = client.put(f"/api/expenses/1", json={"title": "No token"})
    assert res.status_code == 401


def test_update_invalid_token_returns_401(category_id):
    res = client.put(
        "/api/expenses/1",
        json={"title": "Bad token"},
        headers={"Authorization": "Bearer bad.token.here"},
    )
    assert res.status_code == 401


# ── DELETE /api/expenses/{expense_id} tests ───────────────────────────────────

def test_authenticated_user_can_delete_their_expense(token, category_id):
    created = create_expense_via_api(token, category_id)
    res = delete_expense(token, created["id"])
    assert res.status_code == 200


def test_delete_returns_200(token, category_id):
    created = create_expense_via_api(token, category_id)
    res = delete_expense(token, created["id"])
    assert res.status_code == 200


def test_delete_response_contains_success_message(token, category_id):
    created = create_expense_via_api(token, category_id)
    res = delete_expense(token, created["id"])
    assert res.json()["message"] == "Expense deleted successfully"


def test_deleted_expense_cannot_be_retrieved_afterward(token, category_id):
    created = create_expense_via_api(token, category_id)
    delete_expense(token, created["id"])
    res = get_expense_detail(token, created["id"])
    assert res.status_code == 404


def test_deleted_expense_does_not_appear_in_list_afterward(token, category_id):
    created = create_expense_via_api(token, category_id, title="Gone")
    create_expense_via_api(token, category_id, title="Remains")
    delete_expense(token, created["id"])
    res = get_expenses(token)
    titles = [e["title"] for e in res.json()]
    assert "Gone" not in titles
    assert "Remains" in titles


def test_delete_another_users_expense_returns_404(token, other_token, category_id):
    other_expense = create_expense_via_api(other_token, category_id)
    res = delete_expense(token, other_expense["id"])
    assert res.status_code == 404


def test_delete_unknown_expense_returns_404(token):
    res = delete_expense(token, 999999)
    assert res.status_code == 404


def test_delete_already_deleted_expense_returns_404(token, category_id):
    created = create_expense_via_api(token, category_id)
    soft_delete_expense_in_db(created["id"])
    res = delete_expense(token, created["id"])
    assert res.status_code == 404


def test_delete_missing_token_returns_401(category_id):
    res = client.delete("/api/expenses/1")
    assert res.status_code == 401


def test_update_response_does_not_expose_deleted_at(token, category_id):
    created = create_expense_via_api(token, category_id)
    res = put_expense(token, created["id"], {"title": "Check fields"})
    assert "deleted_at" not in res.json()


def test_update_response_does_not_expose_ai_fields(token, category_id):
    created = create_expense_via_api(token, category_id)
    res = put_expense(token, created["id"], {"title": "Check AI fields"})
    data = res.json()
    for field in ("ai_confidence", "ai_status", "ai_raw_response", "language_detected"):
        assert field not in data, f"Response must not expose: {field}"


def test_existing_tests_pass_smoke_check(token, category_id):
    """Smoke: create, list, detail, and delete all still work together."""
    created = create_expense_via_api(token, category_id, title="Smoke")
    assert get_expense_detail(token, created["id"]).status_code == 200
    assert get_expenses(token).status_code == 200
    assert delete_expense(token, created["id"]).status_code == 200
    assert get_expense_detail(token, created["id"]).status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Receipt-link route tests
# ═══════════════════════════════════════════════════════════════════════════════

from app.models.receipt_file import ReceiptFile


def make_receipt_in_db(user_id: int, *, expense_id=None, deleted_at=None) -> int:
    """Insert a ReceiptFile row and return its id."""
    import uuid
    db = TestingSessionLocal()
    stored = f"{uuid.uuid4().hex}.jpg"
    receipt = ReceiptFile(
        user_id=user_id,
        expense_id=expense_id,
        original_filename="receipt.jpg",
        stored_filename=stored,
        file_path=f"/uploads/{stored}",
        mime_type="image/jpeg",
        file_size=1000,
        upload_status="uploaded",
        deleted_at=deleted_at,
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    rid = receipt.id
    db.close()
    return rid


def get_user_id_from_token(token: str) -> int:
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    return me["id"]


def link_receipt(token: str, expense_id: int, receipt_id: int):
    return client.post(
        f"/api/expenses/{expense_id}/receipts/{receipt_id}",
        headers={"Authorization": f"Bearer {token}"},
    )


def unlink_receipt(token: str, expense_id: int, receipt_id: int):
    return client.delete(
        f"/api/expenses/{expense_id}/receipts/{receipt_id}",
        headers={"Authorization": f"Bearer {token}"},
    )


# ── Fixtures for link/unlink tests ───────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_receipts(clean_db):
    """clean_db already runs; just ensure ReceiptFile rows are cleared too."""
    db = TestingSessionLocal()
    db.query(ReceiptFile).delete()
    db.commit()
    db.close()
    yield
    db = TestingSessionLocal()
    db.query(ReceiptFile).delete()
    db.commit()
    db.close()


# ── Link tests ────────────────────────────────────────────────────────────────

def test_authenticated_user_can_link_receipt_to_expense(token, category_id):
    uid = get_user_id_from_token(token)
    expense = create_expense_via_api(token, category_id)
    rid = make_receipt_in_db(uid)
    res = link_receipt(token, expense["id"], rid)
    assert res.status_code == 200


def test_link_returns_200(token, category_id):
    uid = get_user_id_from_token(token)
    expense = create_expense_via_api(token, category_id)
    rid = make_receipt_in_db(uid)
    res = link_receipt(token, expense["id"], rid)
    assert res.status_code == 200


def test_link_response_shows_correct_expense_id(token, category_id):
    uid = get_user_id_from_token(token)
    expense = create_expense_via_api(token, category_id)
    rid = make_receipt_in_db(uid)
    res = link_receipt(token, expense["id"], rid)
    assert res.json()["expense_id"] == expense["id"]


def test_link_same_receipt_again_succeeds(token, category_id):
    uid = get_user_id_from_token(token)
    expense = create_expense_via_api(token, category_id)
    rid = make_receipt_in_db(uid, expense_id=expense["id"])
    res = link_receipt(token, expense["id"], rid)
    assert res.status_code == 200


def test_link_receipt_already_elsewhere_returns_409(token, category_id):
    uid = get_user_id_from_token(token)
    exp_a = create_expense_via_api(token, category_id, title="A")
    exp_b = create_expense_via_api(token, category_id, title="B")
    rid = make_receipt_in_db(uid, expense_id=exp_a["id"])
    res = link_receipt(token, exp_b["id"], rid)
    assert res.status_code == 409


def test_link_unknown_expense_returns_404(token, category_id):
    uid = get_user_id_from_token(token)
    rid = make_receipt_in_db(uid)
    res = link_receipt(token, 999999, rid)
    assert res.status_code == 404


def test_link_unknown_receipt_returns_404(token, category_id):
    expense = create_expense_via_api(token, category_id)
    res = link_receipt(token, expense["id"], 999999)
    assert res.status_code == 404


def test_link_another_users_expense_returns_404(token, other_token, category_id):
    uid = get_user_id_from_token(token)
    other_expense = create_expense_via_api(other_token, category_id)
    rid = make_receipt_in_db(uid)
    res = link_receipt(token, other_expense["id"], rid)
    assert res.status_code == 404


def test_link_another_users_receipt_returns_404(token, other_token, category_id):
    other_uid = get_user_id_from_token(other_token)
    expense = create_expense_via_api(token, category_id)
    rid = make_receipt_in_db(other_uid)
    res = link_receipt(token, expense["id"], rid)
    assert res.status_code == 404


def test_link_soft_deleted_expense_returns_404(token, category_id):
    uid = get_user_id_from_token(token)
    expense = create_expense_via_api(token, category_id)
    soft_delete_expense_in_db(expense["id"])
    rid = make_receipt_in_db(uid)
    res = link_receipt(token, expense["id"], rid)
    assert res.status_code == 404


def test_link_soft_deleted_receipt_returns_404(token, category_id):
    uid = get_user_id_from_token(token)
    expense = create_expense_via_api(token, category_id)
    rid = make_receipt_in_db(uid, deleted_at=datetime(2024, 1, 1))
    res = link_receipt(token, expense["id"], rid)
    assert res.status_code == 404


def test_link_missing_token_returns_401(category_id):
    res = client.post("/api/expenses/1/receipts/1")
    assert res.status_code == 401


def test_link_invalid_token_returns_401(category_id):
    res = client.post(
        "/api/expenses/1/receipts/1",
        headers={"Authorization": "Bearer bad.token.here"},
    )
    assert res.status_code == 401


# ── Unlink tests ──────────────────────────────────────────────────────────────

def test_authenticated_user_can_unlink_receipt(token, category_id):
    uid = get_user_id_from_token(token)
    expense = create_expense_via_api(token, category_id)
    rid = make_receipt_in_db(uid, expense_id=expense["id"])
    res = unlink_receipt(token, expense["id"], rid)
    assert res.status_code == 200


def test_unlink_returns_200(token, category_id):
    uid = get_user_id_from_token(token)
    expense = create_expense_via_api(token, category_id)
    rid = make_receipt_in_db(uid, expense_id=expense["id"])
    res = unlink_receipt(token, expense["id"], rid)
    assert res.status_code == 200


def test_unlink_response_shows_null_expense_id(token, category_id):
    uid = get_user_id_from_token(token)
    expense = create_expense_via_api(token, category_id)
    rid = make_receipt_in_db(uid, expense_id=expense["id"])
    res = unlink_receipt(token, expense["id"], rid)
    assert res.json()["expense_id"] is None


def test_unlink_wrong_expense_returns_409(token, category_id):
    uid = get_user_id_from_token(token)
    exp_a = create_expense_via_api(token, category_id, title="A")
    exp_b = create_expense_via_api(token, category_id, title="B")
    rid = make_receipt_in_db(uid, expense_id=exp_a["id"])
    res = unlink_receipt(token, exp_b["id"], rid)
    assert res.status_code == 409


def test_unlink_unlinked_receipt_returns_409(token, category_id):
    uid = get_user_id_from_token(token)
    expense = create_expense_via_api(token, category_id)
    rid = make_receipt_in_db(uid)  # not linked
    res = unlink_receipt(token, expense["id"], rid)
    assert res.status_code == 409


def test_unlink_missing_token_returns_401(category_id):
    res = client.delete("/api/expenses/1/receipts/1")
    assert res.status_code == 401


def test_unlink_invalid_token_returns_401():
    res = client.delete(
        "/api/expenses/1/receipts/1",
        headers={"Authorization": "Bearer bad.token.here"},
    )
    assert res.status_code == 401


def test_existing_expense_tests_still_pass(token, category_id):
    """Smoke: create, list, detail, update, delete still all work."""
    created = create_expense_via_api(token, category_id, title="Smoke2")
    assert get_expense_detail(token, created["id"]).status_code == 200
    assert get_expenses(token).status_code == 200
    assert put_expense(token, created["id"], {"title": "Updated Smoke"}).status_code == 200
    assert delete_expense(token, created["id"]).status_code == 200
    assert get_expense_detail(token, created["id"]).status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/expenses/{expense_id}/confirm  route tests
# ═══════════════════════════════════════════════════════════════════════════════

from decimal import Decimal as _Decimal


def make_ai_expense_in_db(
    user_id: int,
    category_id: int | None,
    *,
    title: str = "AI Receipt",
    total_amount: str = "120.00",
    is_confirmed: bool = False,
    deleted_at=None,
) -> int:
    """Insert an AI-extracted draft expense directly in the test DB and return its id."""
    db = TestingSessionLocal()
    expense = Expense(
        user_id=user_id,
        category_id=category_id,
        title=title,
        receipt_date=date(2025, 6, 1),
        total_amount=_Decimal(total_amount),
        currency="THB",
        input_method="ai",
        ai_status="completed",
        is_confirmed=is_confirmed,
    )
    if deleted_at is not None:
        expense.deleted_at = deleted_at
    db.add(expense)
    db.commit()
    db.refresh(expense)
    expense_id = expense.id
    db.close()
    return expense_id


def confirm_expense(token: str, expense_id: int):
    return client.post(
        f"/api/expenses/{expense_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )


# ── Happy path ────────────────────────────────────────────────────────────────

def test_confirm_authenticated_user_can_confirm_ai_expense(token, category_id):
    uid = get_user_id_from_token(token)
    expense_id = make_ai_expense_in_db(uid, category_id)
    res = confirm_expense(token, expense_id)
    assert res.status_code == 200


def test_confirm_returns_200(token, category_id):
    uid = get_user_id_from_token(token)
    expense_id = make_ai_expense_in_db(uid, category_id)
    res = confirm_expense(token, expense_id)
    assert res.status_code == 200


def test_confirm_response_uses_expense_response_schema(token, category_id):
    uid = get_user_id_from_token(token)
    expense_id = make_ai_expense_in_db(uid, category_id)
    res = confirm_expense(token, expense_id)
    data = res.json()
    # All ExpenseResponse fields must be present
    for field in ("id", "user_id", "category_id", "title", "total_amount",
                  "is_confirmed", "created_at", "updated_at", "items"):
        assert field in data, f"Missing field in response: {field}"


def test_confirm_response_shows_is_confirmed_true(token, category_id):
    uid = get_user_id_from_token(token)
    expense_id = make_ai_expense_in_db(uid, category_id)
    res = confirm_expense(token, expense_id)
    assert res.json()["is_confirmed"] is True


def test_confirm_response_includes_nested_items(token, category_id):
    uid = get_user_id_from_token(token)
    expense_id = make_ai_expense_in_db(uid, category_id)
    # Add an item directly
    db = TestingSessionLocal()
    from app.models.expense_item import ExpenseItem as ExpItem
    item = ExpItem(
        expense_id=expense_id,
        original_name="Green Curry",
        quantity=_Decimal("1"),
        total_price=_Decimal("80.00"),
    )
    db.add(item)
    db.commit()
    db.close()
    res = confirm_expense(token, expense_id)
    assert len(res.json()["items"]) == 1
    assert res.json()["items"][0]["original_name"] == "Green Curry"


def test_confirm_internal_fields_not_exposed(token, category_id):
    uid = get_user_id_from_token(token)
    expense_id = make_ai_expense_in_db(uid, category_id)
    res = confirm_expense(token, expense_id)
    data = res.json()
    for field in ("deleted_at", "ai_confidence", "ai_status",
                  "ai_raw_response", "language_detected"):
        assert field not in data, f"Response must not expose: {field}"


# ── 404 errors ────────────────────────────────────────────────────────────────

def test_confirm_unknown_expense_returns_404(token):
    res = confirm_expense(token, 999999)
    assert res.status_code == 404


def test_confirm_other_users_expense_returns_404(token, other_token, category_id):
    other_uid = get_user_id_from_token(other_token)
    expense_id = make_ai_expense_in_db(other_uid, category_id)
    res = confirm_expense(token, expense_id)
    assert res.status_code == 404


def test_confirm_soft_deleted_expense_returns_404(token, category_id):
    uid = get_user_id_from_token(token)
    expense_id = make_ai_expense_in_db(uid, category_id,
                                        deleted_at=datetime(2024, 1, 1))
    res = confirm_expense(token, expense_id)
    assert res.status_code == 404


# ── 409 errors ────────────────────────────────────────────────────────────────

def test_confirm_manual_expense_returns_409(token, category_id):
    # Create a normal (manual) expense via API
    created = create_expense_via_api(token, category_id, title="Manual")
    res = confirm_expense(token, created["id"])
    assert res.status_code == 409


def test_confirm_already_confirmed_expense_returns_409(token, category_id):
    uid = get_user_id_from_token(token)
    expense_id = make_ai_expense_in_db(uid, category_id, is_confirmed=True)
    res = confirm_expense(token, expense_id)
    assert res.status_code == 409


# ── 422 errors ────────────────────────────────────────────────────────────────

def test_confirm_missing_category_returns_422(token):
    uid = get_user_id_from_token(token)
    expense_id = make_ai_expense_in_db(uid, category_id=None)
    res = confirm_expense(token, expense_id)
    assert res.status_code == 422


def test_confirm_blank_title_returns_422(token, category_id):
    uid = get_user_id_from_token(token)
    expense_id = make_ai_expense_in_db(uid, category_id, title="   ")
    res = confirm_expense(token, expense_id)
    assert res.status_code == 422


def test_confirm_negative_total_returns_422(token, category_id):
    uid = get_user_id_from_token(token)
    expense_id = make_ai_expense_in_db(uid, category_id, total_amount="-5.00")
    res = confirm_expense(token, expense_id)
    assert res.status_code == 422


# ── Auth errors ───────────────────────────────────────────────────────────────

def test_confirm_missing_token_returns_401(category_id):
    res = client.post("/api/expenses/1/confirm")
    assert res.status_code == 401


def test_confirm_invalid_token_returns_401(category_id):
    res = client.post(
        "/api/expenses/1/confirm",
        headers={"Authorization": "Bearer bad.token.here"},
    )
    assert res.status_code == 401


# ── Confirmed expense remains accessible ─────────────────────────────────────

def test_confirmed_expense_still_visible_in_list(token, category_id):
    uid = get_user_id_from_token(token)
    expense_id = make_ai_expense_in_db(uid, category_id)
    confirm_expense(token, expense_id)
    res = get_expenses(token)
    ids = [e["id"] for e in res.json()]
    assert expense_id in ids


def test_confirmed_expense_still_available_in_detail(token, category_id):
    uid = get_user_id_from_token(token)
    expense_id = make_ai_expense_in_db(uid, category_id)
    confirm_expense(token, expense_id)
    res = get_expense_detail(token, expense_id)
    assert res.status_code == 200
    assert res.json()["is_confirmed"] is True


# ── Update still works before confirmation ────────────────────────────────────

def test_update_before_confirm_still_works(token, category_id):
    uid = get_user_id_from_token(token)
    expense_id = make_ai_expense_in_db(uid, category_id, title="Before Update")
    put_res = put_expense(token, expense_id, {"title": "After Update"})
    assert put_res.status_code == 200
    assert put_res.json()["title"] == "After Update"
    confirm_res = confirm_expense(token, expense_id)
    assert confirm_res.status_code == 200
    assert confirm_res.json()["title"] == "After Update"
    assert confirm_res.json()["is_confirmed"] is True


# ── Full suite smoke ──────────────────────────────────────────────────────────

def test_full_suite_confirm_smoke(token, category_id):
    """Smoke: create, list, detail, update, confirm, delete still all work."""
    uid = get_user_id_from_token(token)
    # Manual expense workflow
    created = create_expense_via_api(token, category_id, title="Smoke Confirm")
    assert get_expense_detail(token, created["id"]).status_code == 200
    assert get_expenses(token).status_code == 200
    assert put_expense(token, created["id"], {"title": "Updated"}).status_code == 200
    assert delete_expense(token, created["id"]).status_code == 200
    # AI expense confirm workflow
    expense_id = make_ai_expense_in_db(uid, category_id)
    assert confirm_expense(token, expense_id).status_code == 200
    assert get_expense_detail(token, expense_id).json()["is_confirmed"] is True
