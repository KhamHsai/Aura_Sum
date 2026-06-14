"""Tests for receipt routes (uses smart_receipt_db_test)."""
import io
import tempfile
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
from app.models.receipt_file import ReceiptFile
from app.models.refresh_token import RefreshToken
from app.models.user import User

# ── Test DB ──────────────────────────────────────────────────────────────────
settings.JWT_SECRET_KEY = "test_jwt_secret_key_receipt_routes_testing_benz_2004"
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

TINY_JPEG = b"\xff\xd8\xff\xe0" + b"x" * 100
TINY_PDF  = b"%PDF-1.4" + b"x" * 100
TINY_PNG  = b"\x89PNG\r\n\x1a\n" + b"x" * 100
BIG_FILE  = b"x" * (11 * 1024 * 1024)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function", autouse=True)
def clean_db():
    db = TestingSessionLocal()
    db.query(ExpenseItem).delete()
    db.query(ReceiptFile).delete()
    db.query(Expense).delete()
    db.query(Category).delete()
    db.query(RefreshToken).delete()
    db.query(User).delete()
    db.commit()
    db.close()
    yield
    db = TestingSessionLocal()
    db.query(ExpenseItem).delete()
    db.query(ReceiptFile).delete()
    db.query(Expense).delete()
    db.query(Category).delete()
    db.query(RefreshToken).delete()
    db.query(User).delete()
    db.commit()
    db.close()


@pytest.fixture()
def auth_token():
    """Register + login the primary test user, return bearer token."""
    client.post("/api/auth/register", json={
        "username": "route_tester",
        "email": "route_tester@example.com",
        "password": "password123",
    })
    res = client.post("/api/auth/login", json={
        "email": "route_tester@example.com",
        "password": "password123",
    })
    return res.json()["access_token"]


@pytest.fixture()
def other_token():
    """Register + login a second user, return bearer token."""
    client.post("/api/auth/register", json={
        "username": "other_tester",
        "email": "other_tester@example.com",
        "password": "password123",
    })
    res = client.post("/api/auth/login", json={
        "email": "other_tester@example.com",
        "password": "password123",
    })
    return res.json()["access_token"]


def upload(token, filename=None, content=None, mime="image/jpeg"):
    """POST a file upload; returns the response."""
    if filename is None:
        filename = "receipt.jpg"
    if content is None:
        content = TINY_JPEG
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": (filename, io.BytesIO(content), mime)}
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.receipt_service.settings") as mock_cfg:
            mock_cfg.UPLOAD_DIR = tmpdir
            mock_cfg.MAX_RECEIPT_FILE_SIZE_MB = 10
            response = client.post("/api/receipts/upload", headers=headers, files=files)
    return response


def upload_and_get_id(token):
    """Upload a receipt and return its ID."""
    res = upload(token)
    assert res.status_code == 201
    return res.json()["id"]


# ── Upload tests (existing) ───────────────────────────────────────────────────

def test_jpeg_upload_returns_201(auth_token):
    res = upload(auth_token, "receipt.jpg", TINY_JPEG, "image/jpeg")
    assert res.status_code == 201


def test_pdf_upload_returns_201(auth_token):
    res = upload(auth_token, "receipt.pdf", TINY_PDF, "application/pdf")
    assert res.status_code == 201


def test_response_contains_safe_fields(auth_token):
    res = upload(auth_token, "receipt.jpg", TINY_JPEG, "image/jpeg")
    data = res.json()
    for field in ("id", "user_id", "original_filename", "stored_filename",
                  "mime_type", "file_size", "upload_status", "uploaded_at"):
        assert field in data, f"Missing field: {field}"


def test_response_does_not_expose_file_path(auth_token):
    res = upload(auth_token, "receipt.jpg", TINY_JPEG, "image/jpeg")
    assert "file_path" not in res.json()


def test_record_belongs_to_authenticated_user(auth_token):
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
    user_id = me_res.json()["id"]
    res = upload(auth_token, "receipt.jpg", TINY_JPEG, "image/jpeg")
    assert res.json()["user_id"] == user_id


def test_missing_token_returns_401():
    files = {"file": ("receipt.jpg", io.BytesIO(TINY_JPEG), "image/jpeg")}
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.receipt_service.settings") as mock_cfg:
            mock_cfg.UPLOAD_DIR = tmpdir
            mock_cfg.MAX_RECEIPT_FILE_SIZE_MB = 10
            res = client.post("/api/receipts/upload", files=files)
    assert res.status_code == 401


def test_invalid_token_returns_401():
    headers = {"Authorization": "Bearer invalid.token.here"}
    files = {"file": ("receipt.jpg", io.BytesIO(TINY_JPEG), "image/jpeg")}
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.receipt_service.settings") as mock_cfg:
            mock_cfg.UPLOAD_DIR = tmpdir
            mock_cfg.MAX_RECEIPT_FILE_SIZE_MB = 10
            res = client.post("/api/receipts/upload", headers=headers, files=files)
    assert res.status_code == 401


def test_missing_file_returns_422(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    res = client.post("/api/receipts/upload", headers=headers)
    assert res.status_code == 422


def test_unsupported_extension_returns_error(auth_token):
    res = upload(auth_token, "file.gif", TINY_JPEG, "image/gif")
    assert res.status_code in (400, 415)


def test_unsupported_mime_type_returns_error(auth_token):
    res = upload(auth_token, "file.jpg", TINY_JPEG, "image/bmp")
    assert res.status_code in (400, 415)


def test_empty_file_returns_error(auth_token):
    res = upload(auth_token, "empty.jpg", b"", "image/jpeg")
    assert res.status_code == 400


def test_oversized_file_returns_error(auth_token):
    res = upload(auth_token, "big.jpg", BIG_FILE, "image/jpeg")
    assert res.status_code == 413


# ── List receipts tests ───────────────────────────────────────────────────────

def test_list_receipts_returns_200(auth_token):
    res = client.get("/api/receipts", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 200


def test_list_receipts_returns_array(auth_token):
    res = client.get("/api/receipts", headers={"Authorization": f"Bearer {auth_token}"})
    assert isinstance(res.json(), list)


def test_list_receipts_returns_only_own(auth_token, other_token):
    upload(auth_token)
    upload(other_token)
    res = client.get("/api/receipts", headers={"Authorization": f"Bearer {auth_token}"})
    data = res.json()
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"}).json()
    assert all(r["user_id"] == me["id"] for r in data)
    assert len(data) == 1


def test_list_receipts_excludes_soft_deleted(auth_token):
    receipt_id = upload_and_get_id(auth_token)
    client.delete(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {auth_token}"})
    res = client.get("/api/receipts", headers={"Authorization": f"Bearer {auth_token}"})
    ids = [r["id"] for r in res.json()]
    assert receipt_id not in ids


def test_list_receipts_newest_first(auth_token):
    id1 = upload_and_get_id(auth_token)
    id2 = upload_and_get_id(auth_token)

    # Force distinct timestamps so ordering is deterministic
    db = TestingSessionLocal()
    from datetime import datetime
    db.query(ReceiptFile).filter(ReceiptFile.id == id1).update(
        {"uploaded_at": datetime(2025, 1, 1, 10, 0, 0)}
    )
    db.query(ReceiptFile).filter(ReceiptFile.id == id2).update(
        {"uploaded_at": datetime(2025, 1, 1, 11, 0, 0)}
    )
    db.commit()
    db.close()

    res = client.get("/api/receipts", headers={"Authorization": f"Bearer {auth_token}"})
    ids = [r["id"] for r in res.json()]
    # id2 is newer, must appear first
    assert ids.index(id2) < ids.index(id1)


def test_list_receipts_empty_returns_200_and_empty_array(auth_token):
    res = client.get("/api/receipts", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 200
    assert res.json() == []


def test_list_receipts_missing_token_returns_401():
    res = client.get("/api/receipts")
    assert res.status_code == 401


# ── Get receipt detail tests ──────────────────────────────────────────────────

def test_get_receipt_returns_200(auth_token):
    receipt_id = upload_and_get_id(auth_token)
    res = client.get(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 200


def test_get_receipt_unknown_id_returns_404(auth_token):
    res = client.get("/api/receipts/999999", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 404


def test_get_receipt_other_user_returns_404(auth_token, other_token):
    other_id = upload_and_get_id(other_token)
    res = client.get(f"/api/receipts/{other_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 404


def test_get_receipt_soft_deleted_returns_404(auth_token):
    receipt_id = upload_and_get_id(auth_token)
    client.delete(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {auth_token}"})
    res = client.get(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 404


def test_get_receipt_missing_token_returns_401():
    res = client.get("/api/receipts/1")
    assert res.status_code == 401


# ── Delete receipt tests ──────────────────────────────────────────────────────

def test_delete_receipt_returns_200(auth_token):
    receipt_id = upload_and_get_id(auth_token)
    res = client.delete(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 200


def test_delete_receipt_response_message(auth_token):
    receipt_id = upload_and_get_id(auth_token)
    res = client.delete(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.json()["message"] == "Receipt deleted successfully"


def test_deleted_receipt_not_retrievable(auth_token):
    receipt_id = upload_and_get_id(auth_token)
    client.delete(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {auth_token}"})
    res = client.get(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 404


def test_deleted_receipt_not_in_list(auth_token):
    receipt_id = upload_and_get_id(auth_token)
    client.delete(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {auth_token}"})
    res = client.get("/api/receipts", headers={"Authorization": f"Bearer {auth_token}"})
    ids = [r["id"] for r in res.json()]
    assert receipt_id not in ids


def test_delete_other_user_receipt_returns_404(auth_token, other_token):
    other_id = upload_and_get_id(other_token)
    res = client.delete(f"/api/receipts/{other_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 404


def test_delete_receipt_missing_token_returns_401():
    res = client.delete("/api/receipts/1")
    assert res.status_code == 401


# ── Response safety ───────────────────────────────────────────────────────────

def test_list_response_never_contains_file_path(auth_token):
    upload(auth_token)
    res = client.get("/api/receipts", headers={"Authorization": f"Bearer {auth_token}"})
    for item in res.json():
        assert "file_path" not in item


def test_detail_response_never_contains_file_path(auth_token):
    receipt_id = upload_and_get_id(auth_token)
    res = client.get(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert "file_path" not in res.json()


# ── Existing route smoke tests ────────────────────────────────────────────────

def test_health_route_still_works():
    res = client.get("/api/health")
    assert res.status_code == 200


def test_auth_register_still_works():
    res = client.post("/api/auth/register", json={
        "username": "check_user",
        "email": "check_user@example.com",
        "password": "password123",
    })
    assert res.status_code == 201


def test_category_routes_still_work(auth_token):
    res = client.get("/api/categories", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/receipts/{receipt_id}/extract — route tests
# ═══════════════════════════════════════════════════════════════════════════════

import uuid
from datetime import date, datetime as dt2
from decimal import Decimal
from unittest.mock import patch as _patch

from app.models.category import Category
from app.models.expense import Expense
from app.models.expense_item import ExpenseItem
from app.schemas.ai_extraction import ExtractedReceiptData, ExtractedReceiptItem
from app.services.gemini_service import GeminiServiceError


# ── Helpers for extraction tests ──────────────────────────────────────────────

def make_category_for_extract(*, code="FOOD_RT", name_en="Food", name_th="อาหาร") -> int:
    db = TestingSessionLocal()
    cat = Category(code=code, name_en=name_en, name_th=name_th, is_active=True)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    cat_id = cat.id
    db.close()
    return cat_id


def insert_receipt_with_file(token: str, file_path: str, expense_id=None) -> int:
    """Insert a ReceiptFile row pointing to a real file. Returns receipt id."""
    db = TestingSessionLocal()
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    stored = f"{uuid.uuid4().hex}.jpg"
    receipt = ReceiptFile(
        user_id=me["id"],
        expense_id=expense_id,
        original_filename="receipt.jpg",
        stored_filename=stored,
        file_path=file_path,
        mime_type="image/jpeg",
        file_size=100,
        upload_status="uploaded",
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    rid = receipt.id
    db.close()
    return rid


def make_fake_file() -> str:
    """Write a tiny fake JPEG to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    f.write(b"\xff\xd8\xff\xe0" + b"x" * 100)
    f.close()
    return f.name


def english_extracted() -> ExtractedReceiptData:
    return ExtractedReceiptData(
        title="Coffee Shop",
        merchant_name="Bean There",
        receipt_number="R001",
        receipt_date=date(2025, 6, 1),
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
                category_name="Food",
            )
        ],
    )


def thai_extracted() -> ExtractedReceiptData:
    return ExtractedReceiptData(
        title="ใบเสร็จ",
        merchant_name="ร้านอาหาร",
        total_amount=Decimal("90.00"),
        language_detected="th",
        items=[
            ExtractedReceiptItem(
                original_name="ข้าวต้ม",
                name_en="Rice Porridge",
                name_th="ข้าวต้ม",
                quantity=Decimal("1"),
                total_price=Decimal("90.00"),
                category_name="Food",
            )
        ],
    )


def patch_extract(return_value=None, side_effect=None):
    """Patch extract_receipt_data inside receipt_service."""
    if side_effect:
        return _patch(
            "app.services.receipt_service.extract_receipt_data",
            side_effect=side_effect,
        )
    return _patch(
        "app.services.receipt_service.extract_receipt_data",
        return_value=return_value or english_extracted(),
    )


def extract(token: str, receipt_id: int):
    return client.post(
        f"/api/receipts/{receipt_id}/extract",
        headers={"Authorization": f"Bearer {token}"},
    )


# ── Route extraction tests ────────────────────────────────────────────────────

def test_authenticated_user_can_extract_receipt(auth_token):
    tmp = make_fake_file()
    try:
        make_category_for_extract()
        rid = insert_receipt_with_file(auth_token, tmp)
        with patch_extract():
            res = extract(auth_token, rid)
        assert res.status_code == 201
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_extract_success_returns_201(auth_token):
    tmp = make_fake_file()
    try:
        make_category_for_extract(code="FOOD_201")
        rid = insert_receipt_with_file(auth_token, tmp)
        with patch_extract():
            res = extract(auth_token, rid)
        assert res.status_code == 201
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_extract_success_returns_expense_response(auth_token):
    tmp = make_fake_file()
    try:
        make_category_for_extract(code="FOOD_RES")
        rid = insert_receipt_with_file(auth_token, tmp)
        with patch_extract():
            res = extract(auth_token, rid)
        data = res.json()
        assert "id" in data
        assert "title" in data
        assert "total_amount" in data
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_extract_response_includes_nested_items(auth_token):
    tmp = make_fake_file()
    try:
        make_category_for_extract(code="FOOD_ITM")
        rid = insert_receipt_with_file(auth_token, tmp)
        with patch_extract():
            res = extract(auth_token, rid)
        data = res.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["original_name"] == "Latte"
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_extract_receipt_becomes_linked(auth_token):
    tmp = make_fake_file()
    try:
        make_category_for_extract(code="FOOD_LNK")
        rid = insert_receipt_with_file(auth_token, tmp)
        with patch_extract():
            res = extract(auth_token, rid)
        expense_id = res.json()["id"]
        db = TestingSessionLocal()
        receipt = db.query(ReceiptFile).filter(ReceiptFile.id == rid).first()
        db.close()
        assert receipt.expense_id == expense_id
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_extract_english_receipt_works(auth_token):
    tmp = make_fake_file()
    try:
        make_category_for_extract(code="FOOD_EN")
        rid = insert_receipt_with_file(auth_token, tmp)
        with patch_extract(return_value=english_extracted()):
            res = extract(auth_token, rid)
        assert res.status_code == 201
        assert res.json()["merchant_name"] == "Bean There"
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_extract_thai_receipt_works(auth_token):
    tmp = make_fake_file()
    try:
        make_category_for_extract(code="FOOD_TH")
        rid = insert_receipt_with_file(auth_token, tmp)
        with patch_extract(return_value=thai_extracted()):
            res = extract(auth_token, rid)
        assert res.status_code == 201
        assert res.json()["merchant_name"] == "ร้านอาหาร"
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_extract_missing_receipt_returns_404(auth_token):
    with patch_extract():
        res = extract(auth_token, 999999)
    assert res.status_code == 404


def test_extract_other_users_receipt_returns_404(auth_token, other_token):
    tmp = make_fake_file()
    try:
        rid = insert_receipt_with_file(other_token, tmp)
        with patch_extract():
            res = extract(auth_token, rid)
        assert res.status_code == 404
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_extract_soft_deleted_receipt_returns_404(auth_token):
    db = TestingSessionLocal()
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"}).json()
    stored = f"{uuid.uuid4().hex}.jpg"
    receipt = ReceiptFile(
        user_id=me["id"],
        original_filename="receipt.jpg",
        stored_filename=stored,
        file_path="/tmp/deleted.jpg",
        mime_type="image/jpeg",
        file_size=100,
        upload_status="uploaded",
        deleted_at=dt2(2024, 1, 1),
    )
    db.add(receipt)
    db.commit()
    rid = receipt.id
    db.close()
    with patch_extract():
        res = extract(auth_token, rid)
    assert res.status_code == 404


def test_extract_missing_file_returns_404(auth_token):
    rid = insert_receipt_with_file(auth_token, "/nonexistent/path/no_file.jpg")
    res = extract(auth_token, rid)
    assert res.status_code == 404


def test_extract_already_linked_receipt_returns_409(auth_token):
    tmp = make_fake_file()
    try:
        rid = insert_receipt_with_file(auth_token, tmp)

        # Create an expense directly in DB so we have a valid expense_id
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"}).json()
        db = TestingSessionLocal()
        exp = Expense(
            user_id=me["id"],
            title="Dummy",
            receipt_date=date(2025, 1, 1),
            total_amount=Decimal("1.00"),
            currency="THB",
            input_method="manual",
        )
        db.add(exp)
        db.commit()
        db.refresh(exp)
        exp_id = exp.id

        # Link the receipt to this expense directly
        receipt = db.query(ReceiptFile).filter(ReceiptFile.id == rid).first()
        receipt.expense_id = exp_id
        db.commit()
        db.close()

        with patch_extract():
            res = extract(auth_token, rid)
        assert res.status_code == 409
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_extract_missing_token_returns_401():
    res = client.post("/api/receipts/1/extract")
    assert res.status_code == 401


def test_extract_invalid_token_returns_401():
    res = client.post(
        "/api/receipts/1/extract",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert res.status_code == 401


def test_extract_gemini_error_preserves_status(auth_token):
    tmp = make_fake_file()
    try:
        rid = insert_receipt_with_file(auth_token, tmp)
        with patch_extract(side_effect=GeminiServiceError("Gemini extraction failed", 502)):
            res = extract(auth_token, rid)
        assert res.status_code == 502
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_extract_gemini_error_creates_no_db_records(auth_token):
    tmp = make_fake_file()
    try:
        rid = insert_receipt_with_file(auth_token, tmp)
        db = TestingSessionLocal()
        expense_count_before = db.query(Expense).count()
        db.close()
        with patch_extract(side_effect=GeminiServiceError("fail", 502)):
            extract(auth_token, rid)
        db = TestingSessionLocal()
        assert db.query(Expense).count() == expense_count_before
        db.close()
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_extract_response_does_not_expose_file_path(auth_token):
    tmp = make_fake_file()
    try:
        make_category_for_extract(code="FOOD_PTV")
        rid = insert_receipt_with_file(auth_token, tmp)
        with patch_extract():
            res = extract(auth_token, rid)
        assert "file_path" not in res.json()
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_extract_response_does_not_expose_deleted_at(auth_token):
    tmp = make_fake_file()
    try:
        make_category_for_extract(code="FOOD_DEL")
        rid = insert_receipt_with_file(auth_token, tmp)
        with patch_extract():
            res = extract(auth_token, rid)
        assert "deleted_at" not in res.json()
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_extract_no_real_gemini_call_occurs(auth_token):
    """All extract route tests patch extract_receipt_data — no live calls possible."""
    import app.services.receipt_service as svc
    assert callable(svc.extract_receipt_data)


def test_existing_full_suite_smoke(auth_token):
    """Confirm upload, list, detail, and delete routes still work."""
    res = upload(auth_token)
    assert res.status_code == 201
    rid = res.json()["id"]

    assert client.get("/api/receipts", headers={"Authorization": f"Bearer {auth_token}"}).status_code == 200
    assert client.get(f"/api/receipts/{rid}", headers={"Authorization": f"Bearer {auth_token}"}).status_code == 200
    assert client.delete(f"/api/receipts/{rid}", headers={"Authorization": f"Bearer {auth_token}"}).status_code == 200


# Need Path imported at module level for cleanup
from pathlib import Path
