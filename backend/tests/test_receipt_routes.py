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
    db.query(ReceiptFile).delete()
    db.query(RefreshToken).delete()
    db.query(User).delete()
    db.commit()
    yield
    db.query(ReceiptFile).delete()
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
