"""Tests for the receipt service (uses smart_receipt_db_test)."""
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.receipt_file import ReceiptFile
from app.models.user import User
from app.services.receipt_service import (
    ReceiptServiceError,
    delete_user_receipt,
    get_user_receipt_by_id,
    get_user_receipts,
    upload_receipt,
)

# ── Test DB setup ────────────────────────────────────────────────────────────
engine = create_engine(settings.TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

TINY_JPEG = b"\xff\xd8\xff\xe0" + b"x" * 100
TINY_PDF  = b"%PDF-1.4" + b"x" * 100


@pytest.fixture(scope="function")
def db():
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def test_user(db):
    """Create a throw-away user for each test."""
    user = User(
        username="svc_tester",
        email="svc_tester@example.com",
        password_hash="hashed",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.query(ReceiptFile).filter(ReceiptFile.user_id == user.id).delete()
    db.delete(user)
    db.commit()


@pytest.fixture(scope="function")
def other_user(db):
    """A second user to test ownership isolation."""
    user = User(
        username="other_svc_tester",
        email="other_svc_tester@example.com",
        password_hash="hashed",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.query(ReceiptFile).filter(ReceiptFile.user_id == user.id).delete()
    db.delete(user)
    db.commit()


def make_receipt(db, user_id, tmpdir, filename="bill.jpg"):
    """Upload a receipt and return the ReceiptFile record."""
    with patch("app.services.receipt_service.settings") as mock_cfg:
        mock_cfg.UPLOAD_DIR = tmpdir
        mock_cfg.MAX_RECEIPT_FILE_SIZE_MB = 10
        return upload_receipt(db, user_id, filename, "image/jpeg", TINY_JPEG)


# ── Upload tests (existing) ───────────────────────────────────────────────────

def test_successful_upload_creates_db_record(db, test_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.receipt_service.settings") as mock_cfg:
            mock_cfg.UPLOAD_DIR = tmpdir
            mock_cfg.MAX_RECEIPT_FILE_SIZE_MB = 10
            result = upload_receipt(db, test_user.id, "bill.jpg", "image/jpeg", TINY_JPEG)
    assert result.id is not None


def test_record_belongs_to_correct_user(db, test_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.receipt_service.settings") as mock_cfg:
            mock_cfg.UPLOAD_DIR = tmpdir
            mock_cfg.MAX_RECEIPT_FILE_SIZE_MB = 10
            result = upload_receipt(db, test_user.id, "bill.jpg", "image/jpeg", TINY_JPEG)
    assert result.user_id == test_user.id


def test_original_filename_is_stored(db, test_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.receipt_service.settings") as mock_cfg:
            mock_cfg.UPLOAD_DIR = tmpdir
            mock_cfg.MAX_RECEIPT_FILE_SIZE_MB = 10
            result = upload_receipt(db, test_user.id, "receipt.pdf", "application/pdf", TINY_PDF)
    assert result.original_filename == "receipt.pdf"


def test_stored_filename_differs_from_original(db, test_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.receipt_service.settings") as mock_cfg:
            mock_cfg.UPLOAD_DIR = tmpdir
            mock_cfg.MAX_RECEIPT_FILE_SIZE_MB = 10
            result = upload_receipt(db, test_user.id, "bill.jpg", "image/jpeg", TINY_JPEG)
    assert result.stored_filename != "bill.jpg"


def test_file_size_and_mime_type_stored(db, test_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.receipt_service.settings") as mock_cfg:
            mock_cfg.UPLOAD_DIR = tmpdir
            mock_cfg.MAX_RECEIPT_FILE_SIZE_MB = 10
            result = upload_receipt(db, test_user.id, "bill.jpg", "image/jpeg", TINY_JPEG)
    assert result.file_size == len(TINY_JPEG)
    assert result.mime_type == "image/jpeg"


def test_physical_file_exists_after_upload(db, test_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.receipt_service.settings") as mock_cfg:
            mock_cfg.UPLOAD_DIR = tmpdir
            mock_cfg.MAX_RECEIPT_FILE_SIZE_MB = 10
            result = upload_receipt(db, test_user.id, "bill.jpg", "image/jpeg", TINY_JPEG)
        assert os.path.isfile(result.file_path)


def test_unsupported_file_is_rejected(db, test_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.receipt_service.settings") as mock_cfg:
            mock_cfg.UPLOAD_DIR = tmpdir
            mock_cfg.MAX_RECEIPT_FILE_SIZE_MB = 10
            with pytest.raises(ReceiptServiceError) as exc_info:
                upload_receipt(db, test_user.id, "file.gif", "image/gif", TINY_JPEG)
    assert exc_info.value.status_code == 415


def test_oversized_file_is_rejected(db, test_user):
    big = b"x" * (11 * 1024 * 1024)
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.receipt_service.settings") as mock_cfg:
            mock_cfg.UPLOAD_DIR = tmpdir
            mock_cfg.MAX_RECEIPT_FILE_SIZE_MB = 10
            with pytest.raises(ReceiptServiceError) as exc_info:
                upload_receipt(db, test_user.id, "big.jpg", "image/jpeg", big)
    assert exc_info.value.status_code == 413


def test_no_db_record_for_invalid_file(db, test_user):
    before = db.query(ReceiptFile).filter(ReceiptFile.user_id == test_user.id).count()
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.receipt_service.settings") as mock_cfg:
            mock_cfg.UPLOAD_DIR = tmpdir
            mock_cfg.MAX_RECEIPT_FILE_SIZE_MB = 10
            with pytest.raises(ReceiptServiceError):
                upload_receipt(db, test_user.id, "file.exe", "application/octet-stream", b"x")
    after = db.query(ReceiptFile).filter(ReceiptFile.user_id == test_user.id).count()
    assert after == before


def test_physical_file_cleaned_up_on_db_failure(db, test_user):
    """If DB commit raises, the saved file must be deleted."""
    saved_paths = []

    original_save = __import__(
        "app.utils.file_utils", fromlist=["save_receipt_file"]
    ).save_receipt_file

    def capturing_save(file_bytes, stored_filename, upload_dir):
        path = original_save(file_bytes, stored_filename, upload_dir)
        saved_paths.append(path)
        return path

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.receipt_service.settings") as mock_cfg:
            mock_cfg.UPLOAD_DIR = tmpdir
            mock_cfg.MAX_RECEIPT_FILE_SIZE_MB = 10
            with patch("app.services.receipt_service.save_receipt_file", side_effect=capturing_save):
                with patch.object(db, "commit", side_effect=Exception("DB down")):
                    with pytest.raises(Exception, match="DB down"):
                        upload_receipt(db, test_user.id, "bill.jpg", "image/jpeg", TINY_JPEG)

        # Physical file must have been removed
        for path in saved_paths:
            assert not os.path.isfile(path)


# ── get_user_receipts tests ───────────────────────────────────────────────────

def test_get_user_receipts_returns_only_own_receipts(db, test_user, other_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        make_receipt(db, test_user.id, tmpdir)
        make_receipt(db, other_user.id, tmpdir)
        results = get_user_receipts(db, test_user.id)
    assert all(r.user_id == test_user.id for r in results)
    assert len(results) == 1


def test_get_user_receipts_ordered_newest_first(db, test_user):
    from datetime import timedelta
    with tempfile.TemporaryDirectory() as tmpdir:
        r1 = make_receipt(db, test_user.id, tmpdir, "first.jpg")
        r2 = make_receipt(db, test_user.id, tmpdir, "second.jpg")

    # Force distinct uploaded_at so ordering is deterministic
    r1.uploaded_at = datetime(2025, 1, 1, 10, 0, 0)
    r2.uploaded_at = datetime(2025, 1, 1, 11, 0, 0)
    db.commit()

    results = get_user_receipts(db, test_user.id)
    ids = [r.id for r in results]
    # r2 is newer, must come first
    assert ids.index(r2.id) < ids.index(r1.id)


def test_get_user_receipts_excludes_soft_deleted(db, test_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        r = make_receipt(db, test_user.id, tmpdir)
        r.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        results = get_user_receipts(db, test_user.id)
    assert len(results) == 0


def test_get_user_receipts_excludes_other_users(db, test_user, other_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        make_receipt(db, other_user.id, tmpdir)
        results = get_user_receipts(db, test_user.id)
    assert results == []


def test_get_user_receipts_empty_for_new_user(db, test_user):
    results = get_user_receipts(db, test_user.id)
    assert results == []


# ── get_user_receipt_by_id tests ─────────────────────────────────────────────

def test_get_user_receipt_by_id_returns_owned_receipt(db, test_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        r = make_receipt(db, test_user.id, tmpdir)
        result = get_user_receipt_by_id(db, test_user.id, r.id)
    assert result is not None
    assert result.id == r.id


def test_get_user_receipt_by_id_unknown_id_returns_none(db, test_user):
    result = get_user_receipt_by_id(db, test_user.id, 999999)
    assert result is None


def test_get_user_receipt_by_id_other_user_returns_none(db, test_user, other_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        r = make_receipt(db, other_user.id, tmpdir)
        result = get_user_receipt_by_id(db, test_user.id, r.id)
    assert result is None


def test_get_user_receipt_by_id_soft_deleted_returns_none(db, test_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        r = make_receipt(db, test_user.id, tmpdir)
        r.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        result = get_user_receipt_by_id(db, test_user.id, r.id)
    assert result is None


# ── delete_user_receipt tests ─────────────────────────────────────────────────

def test_delete_user_receipt_sets_deleted_at(db, test_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        r = make_receipt(db, test_user.id, tmpdir)
        success = delete_user_receipt(db, test_user.id, r.id)
    assert success is True
    db.refresh(r)
    assert r.deleted_at is not None


def test_delete_user_receipt_row_still_exists(db, test_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        r = make_receipt(db, test_user.id, tmpdir)
        delete_user_receipt(db, test_user.id, r.id)
    row = db.query(ReceiptFile).filter(ReceiptFile.id == r.id).first()
    assert row is not None


def test_delete_user_receipt_physical_file_still_exists(db, test_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        r = make_receipt(db, test_user.id, tmpdir)
        file_path = r.file_path
        delete_user_receipt(db, test_user.id, r.id)
        assert os.path.isfile(file_path)


def test_delete_user_receipt_unknown_id_returns_false(db, test_user):
    result = delete_user_receipt(db, test_user.id, 999999)
    assert result is False


def test_delete_user_receipt_other_user_returns_false(db, test_user, other_user):
    with tempfile.TemporaryDirectory() as tmpdir:
        r = make_receipt(db, other_user.id, tmpdir)
        result = delete_user_receipt(db, test_user.id, r.id)
    assert result is False
