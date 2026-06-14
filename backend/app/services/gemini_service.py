"""Gemini AI receipt-extraction service.

Public API
----------
    extract_receipt_data(file_path, mime_type) -> ExtractedReceiptData
    GeminiServiceError

The function reads the receipt file, calls Gemini, and returns a
validated ExtractedReceiptData object.  No database rows are created here.

The google-genai SDK client is built inside _build_client() so tests can
patch that single function without touching real network calls.
"""

import json
import re
from pathlib import Path

import google.genai as genai
import google.genai.types as genai_types
from pydantic import ValidationError

from app.config import settings
from app.schemas.ai_extraction import ExtractedReceiptData

# ---------------------------------------------------------------------------
# Supported MIME types (same as the receipt upload feature)
# ---------------------------------------------------------------------------

SUPPORTED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    }
)

# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class GeminiServiceError(Exception):
    """Raised when Gemini extraction cannot complete.

    status_code follows HTTP conventions so the route layer can forward it
    without needing to inspect the message.
    """

    def __init__(self, message: str, status_code: int = 502) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ---------------------------------------------------------------------------
# Extraction prompt
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """You are extracting structured data from a receipt image or PDF.

Instructions:
- The receipt is written in English or Thai only.
- Return JSON only. Do not include Markdown. Do not include code fences.
- Do not invent values. Use null when a value is unavailable.
- Use ISO date format YYYY-MM-DD for receipt_date.
- Use 24-hour time HH:MM:SS for receipt_time when available.
- Use uppercase currency codes (e.g. THB, USD). Do not include currency symbols or commas in numbers.
- Use plain decimal numbers (e.g. 150.00) for all monetary values.
- Detect the receipt language as "en" for English or "th" for Thai only.
- For each line item, provide both English (name_en) and Thai (name_th) names when possible.
- Set ai_confidence as a decimal between 0.00 and 1.00 reflecting your confidence.

Return exactly this JSON structure (no extra fields, no surrounding text):
{
  "title": null,
  "merchant_name": null,
  "receipt_number": null,
  "receipt_date": null,
  "receipt_time": null,
  "document_type": null,
  "payment_method": null,
  "currency": "THB",
  "subtotal": null,
  "tax_amount": null,
  "discount_amount": null,
  "total_amount": "0.00",
  "language_detected": "th",
  "ai_confidence": "0.90",
  "items": [
    {
      "original_name": null,
      "name_en": null,
      "name_th": null,
      "quantity": null,
      "unit": null,
      "unit_price": null,
      "discount_amount": null,
      "total_price": null,
      "category_name": null
    }
  ]
}"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_client() -> genai.Client:
    """Create and return a Gemini SDK client.

    Kept in one function so tests can patch it with a single mock target.
    Raises GeminiServiceError when no API key is configured.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise GeminiServiceError(
            "Gemini API key is not configured", status_code=503
        )
    return genai.Client(api_key=api_key)


def _clean_response_text(text: str) -> str:
    """Strip whitespace and remove one surrounding ```json … ``` fence if present."""
    text = text.strip()
    # Remove optional ```json ... ``` or ``` ... ``` fence
    fenced = re.match(r"^```(?:json)?\s*([\s\S]*?)```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    return text


def _parse_and_validate(raw_text: str) -> ExtractedReceiptData:
    """Parse JSON text and validate it as ExtractedReceiptData."""
    cleaned = _clean_response_text(raw_text)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiServiceError("Gemini returned invalid JSON") from exc

    try:
        return ExtractedReceiptData.model_validate(payload)
    except ValidationError as exc:
        raise GeminiServiceError("Gemini response validation failed") from exc


# ---------------------------------------------------------------------------
# Public extraction function
# ---------------------------------------------------------------------------


def extract_receipt_data(
    file_path: Path | str,
    mime_type: str,
) -> ExtractedReceiptData:
    """Extract structured receipt data using Gemini.

    Steps:
    1. Validate API configuration.
    2. Validate MIME type.
    3. Confirm the file exists.
    4. Read file bytes.
    5. Send prompt + file to Gemini.
    6. Parse and validate the response.
    7. Return ExtractedReceiptData.

    Does NOT touch the database.
    Does NOT create Expense or ExpenseItem records.
    Does NOT link receipts to expenses.
    """
    # 1. Build client (raises GeminiServiceError if key is missing)
    client = _build_client()

    # 2. Validate MIME type
    if mime_type not in SUPPORTED_MIME_TYPES:
        raise GeminiServiceError(
            f"Unsupported receipt file type: {mime_type}", status_code=415
        )

    # 3. Confirm the file exists
    path = Path(file_path)
    if not path.is_file():
        raise GeminiServiceError("Receipt file not found", status_code=404)

    # 4. Read file bytes
    file_bytes = path.read_bytes()

    # 5. Send to Gemini
    image_part = genai_types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[EXTRACTION_PROMPT, image_part],
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
    except GeminiServiceError:
        raise
    except Exception as exc:
        # Do not leak provider details (they may contain the model name, endpoint,
        # or other internal information).  Use a generic message.
        raise GeminiServiceError("Gemini extraction failed") from exc

    # 6. Extract text from response
    response_text = response.text if hasattr(response, "text") else None
    if not response_text or not response_text.strip():
        raise GeminiServiceError("Gemini returned an empty response")

    # 7. Parse, validate, return
    return _parse_and_validate(response_text)
