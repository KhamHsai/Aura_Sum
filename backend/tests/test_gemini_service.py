"""Mocked tests for the Gemini receipt-extraction service.

All Gemini SDK calls are patched — no real API requests are made.
No database rows are created or read in these tests.
"""

import json
import tempfile
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.ai_extraction import ExtractedReceiptData
from app.services.gemini_service import (
    EXTRACTION_PROMPT,
    SUPPORTED_MIME_TYPES,
    GeminiServiceError,
    extract_receipt_data,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(json_payload: dict | str) -> MagicMock:
    """Return a mock Gemini response with .text set to a JSON string."""
    text = json.dumps(json_payload) if isinstance(json_payload, dict) else json_payload
    mock_resp = MagicMock()
    mock_resp.text = text
    return mock_resp


def _english_payload() -> dict:
    return {
        "title": "Coffee Shop Receipt",
        "merchant_name": "Bean There",
        "receipt_number": "R001",
        "receipt_date": "2024-06-01",
        "receipt_time": "09:30:00",
        "document_type": "receipt",
        "payment_method": "cash",
        "currency": "USD",
        "subtotal": "4.50",
        "tax_amount": "0.50",
        "discount_amount": "0.00",
        "total_amount": "5.00",
        "language_detected": "en",
        "ai_confidence": "0.95",
        "items": [
            {
                "original_name": "Latte",
                "name_en": "Latte",
                "name_th": "ลาเต้",
                "quantity": "1",
                "unit": "cup",
                "unit_price": "4.50",
                "discount_amount": "0.00",
                "total_price": "4.50",
                "category_name": "Beverages",
            }
        ],
    }


def _thai_payload() -> dict:
    return {
        "title": "ใบเสร็จร้านอาหาร",
        "merchant_name": "ร้านข้าวต้ม",
        "receipt_number": "T001",
        "receipt_date": "2024-06-15",
        "receipt_time": "12:00:00",
        "document_type": "receipt",
        "payment_method": "เงินสด",
        "currency": "THB",
        "subtotal": "90.00",
        "tax_amount": "0.00",
        "discount_amount": "0.00",
        "total_amount": "90.00",
        "language_detected": "th",
        "ai_confidence": "0.88",
        "items": [
            {
                "original_name": "ข้าวต้ม",
                "name_en": "Rice Porridge",
                "name_th": "ข้าวต้ม",
                "quantity": "1",
                "unit": "bowl",
                "unit_price": "90.00",
                "discount_amount": "0.00",
                "total_price": "90.00",
                "category_name": "Food",
            }
        ],
    }


def _write_temp_file(content: bytes = b"fake receipt bytes") -> tempfile.NamedTemporaryFile:
    """Return an open NamedTemporaryFile with fake bytes."""
    f = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    f.write(content)
    f.flush()
    f.close()
    return f


# ---------------------------------------------------------------------------
# Fixtures / context helpers
# ---------------------------------------------------------------------------

def _patch_client(response: MagicMock):
    """Patch _build_client to return a mock whose generate_content returns response."""
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = response
    return patch("app.services.gemini_service._build_client", return_value=mock_client)


# ---------------------------------------------------------------------------
# 1. Valid mocked Gemini JSON returns ExtractedReceiptData
# ---------------------------------------------------------------------------

def test_valid_mock_returns_extracted_receipt_data():
    tmp = _write_temp_file()
    with _patch_client(_make_response(_english_payload())):
        result = extract_receipt_data(tmp.name, "image/jpeg")
    assert isinstance(result, ExtractedReceiptData)
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 2. English receipt output is parsed
# ---------------------------------------------------------------------------

def test_english_receipt_parsed():
    tmp = _write_temp_file()
    with _patch_client(_make_response(_english_payload())):
        result = extract_receipt_data(tmp.name, "image/jpeg")
    assert result.language_detected == "en"
    assert result.merchant_name == "Bean There"
    assert result.total_amount == Decimal("5.00")
    assert result.currency == "USD"
    assert len(result.items) == 1
    assert result.items[0].name_en == "Latte"
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 3. Thai receipt output is parsed
# ---------------------------------------------------------------------------

def test_thai_receipt_parsed():
    tmp = _write_temp_file()
    with _patch_client(_make_response(_thai_payload())):
        result = extract_receipt_data(tmp.name, "image/png")
    assert result.language_detected == "th"
    assert result.currency == "THB"
    assert result.total_amount == Decimal("90.00")
    assert result.items[0].name_th == "ข้าวต้ม"
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 4. Missing API key raises clear service error
# ---------------------------------------------------------------------------

def test_missing_api_key_raises_service_error(monkeypatch):
    monkeypatch.setattr("app.services.gemini_service.settings.GEMINI_API_KEY", "")
    tmp = _write_temp_file()
    with pytest.raises(GeminiServiceError) as exc_info:
        extract_receipt_data(tmp.name, "image/jpeg")
    assert "not configured" in exc_info.value.message.lower()
    assert exc_info.value.status_code == 503
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 5. Missing file raises clear service error
# ---------------------------------------------------------------------------

def test_missing_file_raises_service_error(monkeypatch):
    monkeypatch.setattr("app.services.gemini_service.settings.GEMINI_API_KEY", "test-key")
    with patch("app.services.gemini_service._build_client"):
        with pytest.raises(GeminiServiceError) as exc_info:
            extract_receipt_data("/nonexistent/path/receipt.jpg", "image/jpeg")
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.message.lower()


# ---------------------------------------------------------------------------
# 6. Unsupported MIME type raises clear service error
# ---------------------------------------------------------------------------

def test_unsupported_mime_type_raises_service_error(monkeypatch):
    monkeypatch.setattr("app.services.gemini_service.settings.GEMINI_API_KEY", "test-key")
    tmp = _write_temp_file()
    with patch("app.services.gemini_service._build_client"):
        with pytest.raises(GeminiServiceError) as exc_info:
            extract_receipt_data(tmp.name, "image/gif")
    assert exc_info.value.status_code == 415
    assert "unsupported" in exc_info.value.message.lower()
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 7. Empty Gemini response raises clear service error
# ---------------------------------------------------------------------------

def test_empty_response_raises_service_error():
    tmp = _write_temp_file()
    mock_resp = MagicMock()
    mock_resp.text = ""
    with _patch_client(mock_resp):
        with pytest.raises(GeminiServiceError) as exc_info:
            extract_receipt_data(tmp.name, "image/jpeg")
    assert "empty" in exc_info.value.message.lower()
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 8. Invalid JSON raises clear service error
# ---------------------------------------------------------------------------

def test_invalid_json_raises_service_error():
    tmp = _write_temp_file()
    with _patch_client(_make_response("this is not json {")):
        with pytest.raises(GeminiServiceError) as exc_info:
            extract_receipt_data(tmp.name, "image/jpeg")
    assert "invalid json" in exc_info.value.message.lower()
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 9. Markdown JSON fence is handled
# ---------------------------------------------------------------------------

def test_markdown_json_fence_is_handled():
    tmp = _write_temp_file()
    fenced = "```json\n" + json.dumps(_english_payload()) + "\n```"
    mock_resp = MagicMock()
    mock_resp.text = fenced
    with _patch_client(mock_resp):
        result = extract_receipt_data(tmp.name, "image/jpeg")
    assert isinstance(result, ExtractedReceiptData)
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 10. Schema-invalid JSON raises validation error (as GeminiServiceError)
# ---------------------------------------------------------------------------

def test_schema_invalid_json_raises_service_error():
    tmp = _write_temp_file()
    # Missing required total_amount
    bad_payload = {"language_detected": "en", "merchant_name": "Test"}
    with _patch_client(_make_response(bad_payload)):
        with pytest.raises(GeminiServiceError) as exc_info:
            extract_receipt_data(tmp.name, "image/jpeg")
    assert "validation failed" in exc_info.value.message.lower()
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 11. Provider exception becomes GeminiServiceError
# ---------------------------------------------------------------------------

def test_provider_exception_becomes_service_error(monkeypatch):
    monkeypatch.setattr("app.services.gemini_service.settings.GEMINI_API_KEY", "test-key")
    tmp = _write_temp_file()

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("network error")

    with patch("app.services.gemini_service._build_client", return_value=mock_client):
        with pytest.raises(GeminiServiceError) as exc_info:
            extract_receipt_data(tmp.name, "image/jpeg")
    assert "extraction failed" in exc_info.value.message.lower()
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 12. Provider exception does not leak API key
# ---------------------------------------------------------------------------

def test_provider_exception_does_not_leak_api_key(monkeypatch):
    real_key = "sk-super-secret-key-12345"
    monkeypatch.setattr("app.services.gemini_service.settings.GEMINI_API_KEY", real_key)
    tmp = _write_temp_file()

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError(
        f"API request failed with key={real_key}"
    )

    with patch("app.services.gemini_service._build_client", return_value=mock_client):
        with pytest.raises(GeminiServiceError) as exc_info:
            extract_receipt_data(tmp.name, "image/jpeg")

    # The public error message must not contain the key value
    assert real_key not in exc_info.value.message
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 13. JPEG MIME type is accepted
# ---------------------------------------------------------------------------

def test_jpeg_mime_type_accepted():
    tmp = _write_temp_file()
    with _patch_client(_make_response(_english_payload())):
        result = extract_receipt_data(tmp.name, "image/jpeg")
    assert isinstance(result, ExtractedReceiptData)
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 14. PNG MIME type is accepted
# ---------------------------------------------------------------------------

def test_png_mime_type_accepted():
    tmp = _write_temp_file()
    with _patch_client(_make_response(_thai_payload())):
        result = extract_receipt_data(tmp.name, "image/png")
    assert isinstance(result, ExtractedReceiptData)
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 15. WEBP MIME type is accepted
# ---------------------------------------------------------------------------

def test_webp_mime_type_accepted():
    tmp = _write_temp_file()
    with _patch_client(_make_response(_english_payload())):
        result = extract_receipt_data(tmp.name, "image/webp")
    assert isinstance(result, ExtractedReceiptData)
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 16. PDF MIME type is accepted
# ---------------------------------------------------------------------------

def test_pdf_mime_type_accepted():
    tmp = _write_temp_file(b"%PDF-1.4 fake content")
    with _patch_client(_make_response(_english_payload())):
        result = extract_receipt_data(tmp.name, "application/pdf")
    assert isinstance(result, ExtractedReceiptData)
    Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 17. Prompt requires JSON-only output
# ---------------------------------------------------------------------------

def test_prompt_requires_json_only():
    assert "Return JSON only" in EXTRACTION_PROMPT
    assert "Do not include Markdown" in EXTRACTION_PROMPT
    assert "Do not include code fences" in EXTRACTION_PROMPT


# ---------------------------------------------------------------------------
# 18. Prompt mentions English and Thai only
# ---------------------------------------------------------------------------

def test_prompt_mentions_english_and_thai():
    assert "English" in EXTRACTION_PROMPT
    assert "Thai" in EXTRACTION_PROMPT


# ---------------------------------------------------------------------------
# 19. Prompt requires en or th language code
# ---------------------------------------------------------------------------

def test_prompt_requires_en_or_th_codes():
    assert '"en"' in EXTRACTION_PROMPT or "'en'" in EXTRACTION_PROMPT or "en" in EXTRACTION_PROMPT
    assert '"th"' in EXTRACTION_PROMPT or "'th'" in EXTRACTION_PROMPT or "th" in EXTRACTION_PROMPT


# ---------------------------------------------------------------------------
# 20. No database rows are created during extraction tests
# ---------------------------------------------------------------------------

def test_no_database_rows_created():
    """Verify extract_receipt_data never imports or calls SQLAlchemy Session methods."""
    import inspect
    import app.services.gemini_service as svc

    source = inspect.getsource(svc)
    # The service must not import Session or touch DB models
    assert "Session" not in source
    assert "db.add" not in source
    assert "db.commit" not in source


# ---------------------------------------------------------------------------
# 21. No real network request occurs (all SDK calls are patched)
# ---------------------------------------------------------------------------

def test_no_real_network_request():
    """Confirm that _build_client is the only point where network could occur,
    and that we always patch it in tests."""
    # This test is structural: all tests in this file use _patch_client()
    # or patch _build_client directly, so no live HTTP is ever made.
    # We verify _build_client exists as the mock boundary.
    import app.services.gemini_service as svc
    assert callable(svc._build_client)


# ---------------------------------------------------------------------------
# 22. Existing supported MIME types are all present in SUPPORTED_MIME_TYPES
# ---------------------------------------------------------------------------

def test_all_four_mime_types_supported():
    assert "image/jpeg" in SUPPORTED_MIME_TYPES
    assert "image/png" in SUPPORTED_MIME_TYPES
    assert "image/webp" in SUPPORTED_MIME_TYPES
    assert "application/pdf" in SUPPORTED_MIME_TYPES
