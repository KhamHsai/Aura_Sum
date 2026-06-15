"""Tests for file utility helpers (no database required)."""
import os
import tempfile

import pytest

from app.utils.file_utils import (
    delete_saved_file,
    generate_stored_filename,
    save_receipt_file,
    validate_receipt_file,
)

MAX = 10 * 1024 * 1024  # 10 MB

TINY_JPEG = b"\xff\xd8\xff\xe0" + b"x" * 100  # minimal JPEG-ish bytes
TINY_PNG  = b"\x89PNG\r\n\x1a\n" + b"x" * 100
TINY_WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"x" * 100
TINY_PDF  = b"%PDF-1.4" + b"x" * 100


# ── validate_receipt_file ────────────────────────────────────────────────────

def test_valid_jpeg_accepted():
    validate_receipt_file("photo.jpg", "image/jpeg", TINY_JPEG, MAX)

def test_valid_png_accepted():
    validate_receipt_file("scan.png", "image/png", TINY_PNG, MAX)

def test_valid_webp_accepted():
    validate_receipt_file("img.webp", "image/webp", TINY_WEBP, MAX)

def test_valid_pdf_accepted():
    validate_receipt_file("bill.pdf", "application/pdf", TINY_PDF, MAX)

def test_unsupported_extension_rejected():
    with pytest.raises(ValueError, match="Unsupported receipt file type"):
        validate_receipt_file("file.gif", "image/gif", TINY_JPEG, MAX)

def test_unsupported_mime_type_rejected():
    with pytest.raises(ValueError, match="Unsupported receipt file type"):
        validate_receipt_file("file.jpg", "image/gif", TINY_JPEG, MAX)

def test_missing_filename_rejected():
    with pytest.raises(ValueError, match="Invalid receipt filename"):
        validate_receipt_file("", "image/jpeg", TINY_JPEG, MAX)

def test_empty_file_rejected():
    with pytest.raises(ValueError, match="Receipt file is empty"):
        validate_receipt_file("photo.jpg", "image/jpeg", b"", MAX)

def test_oversized_file_rejected():
    big = b"x" * (MAX + 1)
    with pytest.raises(ValueError, match="Receipt file is too large"):
        validate_receipt_file("photo.jpg", "image/jpeg", big, MAX)


# ── generate_stored_filename ─────────────────────────────────────────────────

def test_generated_filename_is_unique():
    a = generate_stored_filename("photo.jpg")
    b = generate_stored_filename("photo.jpg")
    assert a != b

def test_generated_filename_preserves_extension():
    name = generate_stored_filename("receipt.pdf")
    assert name.endswith(".pdf")

def test_generated_filename_preserves_jpeg_extension():
    name = generate_stored_filename("img.jpeg")
    assert name.endswith(".jpeg")

def test_generated_filename_lowercases_extension():
    name = generate_stored_filename("SCAN.PNG")
    assert name.endswith(".png")


# ── save_receipt_file & delete_saved_file ────────────────────────────────────

def test_file_saves_inside_configured_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        stored = generate_stored_filename("bill.pdf")
        path = save_receipt_file(TINY_PDF, stored, tmpdir)
        assert os.path.isfile(path)
        assert path.startswith(tmpdir)

def test_cleanup_deletes_existing_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        stored = generate_stored_filename("bill.pdf")
        path = save_receipt_file(TINY_PDF, stored, tmpdir)
        assert os.path.isfile(path)
        delete_saved_file(path)
        assert not os.path.isfile(path)

def test_cleanup_ignores_missing_file():
    # Should not raise even if the file never existed
    delete_saved_file("/tmp/nonexistent_receipt_123456.pdf")
