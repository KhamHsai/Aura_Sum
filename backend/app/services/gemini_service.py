"""AI receipt-extraction service — powered by OpenRouter.

Public API
----------
    extract_receipt_data(file_path, mime_type) -> ExtractedReceiptData
    GeminiServiceError   (name kept for backward compatibility)

Sends the receipt image to OpenRouter using the OpenAI-compatible API.
The model is configurable via OPENROUTER_MODEL in .env.
"""

import base64
import json
import re
from pathlib import Path

from openai import OpenAI

from app.config import settings
from app.schemas.ai_extraction import ExtractedReceiptData

# ---------------------------------------------------------------------------
# Supported MIME types
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
# Custom exception (name kept so routes don't need changes)
# ---------------------------------------------------------------------------


class GeminiServiceError(Exception):
    """Raised when AI extraction cannot complete."""

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
- Do not invent values. Use null only when a value is truly not visible on the receipt.
- IMPORTANT: Read every detail carefully from the receipt image before setting any field to null.
- receipt_date: READ the actual date printed on the receipt (look for วันที่, Date, or any date format). Use ISO format YYYY-MM-DD. IMPORTANT: Thai receipts use Buddhist Era (BE) years — subtract 543 to convert to CE (e.g. 69 → 2026, 67 → 2024, 68 → 2025). A 2-digit year like "69" means BE 2569 = CE 2026. Do NOT use today's date.
- receipt_time: READ the time printed on the receipt if visible. Use 24-hour HH:MM:SS format.
- tax_id: READ the tax ID, VAT registration number, เลขประจำตัวผู้เสียภาษี, or business registration number printed on the receipt. This is often a 13-digit number in Thailand.
- receipt_number: READ the receipt/invoice/bill number printed on the receipt (เลขที่, No., Receipt No., etc.).
- paid_to: READ the shop name, restaurant name, or business name at the top of the receipt.
- payment_method: READ how the payment was made (Cash, Card, QR, โอนเงิน, เงินสด, etc.) if shown.
- subtotal: READ the subtotal amount before tax/discount if shown separately.
- tax_amount: READ the VAT or tax amount if shown separately.
- discount_amount: READ the discount amount if any.
- total_amount: READ the final total amount paid. This is REQUIRED and must not be null.
- Use uppercase currency codes (THB, USD). Do not include currency symbols or commas in numbers.
- Use plain decimal numbers (e.g. 150.00) for all monetary values.
- Detect the receipt language as "en" for English or "th" for Thai only.
- Extract ALL line items from the receipt — every individual product, dish, or service listed.
- For each line item, read the original name exactly as printed, and provide both English (name_en) and Thai (name_th) translations.
- Set ai_confidence as a decimal between 0.00 and 1.00 reflecting your confidence.
- category_name: guess the best expense category in English using EXACTLY one of these values: Food & Drink, Transport, Shopping, Accommodation, Healthcare, Entertainment, Education, Utilities, Other. For restaurants and food purchases use "Food & Drink".

Return exactly this JSON structure (no extra fields, no surrounding text):
{
  "paid_to": null,
  "tax_id": null,
  "category_name": null,
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
    },
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


def _build_client() -> OpenAI:
    """Create and return an OpenRouter client.

    Raises GeminiServiceError when no API key is configured.
    """
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        raise GeminiServiceError(
            "OpenRouter API key is not configured", status_code=503
        )
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def _clean_response_text(text: str) -> str:
    """Strip whitespace and remove one surrounding ```json … ``` fence if present."""
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*([\s\S]*?)```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    return text


def _parse_and_validate(raw_text: str) -> ExtractedReceiptData:
    """Parse JSON text and validate it as ExtractedReceiptData."""
    from pydantic import ValidationError

    cleaned = _clean_response_text(raw_text)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiServiceError("AI returned invalid JSON") from exc

    try:
        return ExtractedReceiptData.model_validate(payload)
    except ValidationError as exc:
        raise GeminiServiceError("AI response validation failed") from exc


# ---------------------------------------------------------------------------
# Public extraction function
# ---------------------------------------------------------------------------


def extract_receipt_data(
    file_path: Path | str,
    mime_type: str,
) -> ExtractedReceiptData:
    """Extract structured receipt data using OpenRouter vision model.

    Steps:
    1. Validate API configuration.
    2. Validate MIME type.
    3. Confirm the file exists.
    4. Read and base64-encode file bytes.
    5. Send prompt + image to OpenRouter.
    6. Parse and validate the response.
    7. Return ExtractedReceiptData.
    """
    # 1. Build client
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

    # 4. Read and base64-encode
    file_bytes = path.read_bytes()
    b64_image = base64.b64encode(file_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64_image}"

    # 5. Send to OpenRouter
    try:
        response = client.chat.completions.create(
            model=settings.OPENROUTER_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                    ],
                }
            ],
        )
    except GeminiServiceError:
        raise
    except Exception as exc:
        err_str = str(exc)
        if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
            raise GeminiServiceError(
                "AI API quota exceeded. Please wait a moment and try again.",
                status_code=429,
            ) from exc
        raise GeminiServiceError("AI extraction failed") from exc

    # 6. Extract text from response
    response_text = response.choices[0].message.content if response.choices else None
    if not response_text or not response_text.strip():
        raise GeminiServiceError("AI returned an empty response")

    # 7. Parse, validate, return
    return _parse_and_validate(response_text)
