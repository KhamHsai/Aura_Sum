"""AI receipt-extraction service — powered by OpenRouter.

Strategy: two-step pipeline
  Step 1 — READ (vision AI call): Ask AI to transcribe all text from the receipt image.
  Step 2 — PARSE (our Python code): Extract structured fields from that plain text.

This is better than asking one weak model to do everything at once because:
- The model is reliable at reading/transcribing text from images
- Python regex/parsing is 100% reliable at converting what was read into structured data
- No second AI call needed → faster, no quota waste

The raw OCR text is also passed back so receipt_service can apply additional
fallbacks (category keyword matching, etc.).

Public API
----------
    extract_receipt_data(file_path, mime_type) -> (ExtractedReceiptData, str)
    GeminiServiceError
"""

import base64
import json
import re
from datetime import date, time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from openai import OpenAI

from app.config import settings
from app.schemas.ai_extraction import ExtractedReceiptData, ExtractedReceiptItem

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
# Custom exception
# ---------------------------------------------------------------------------


class GeminiServiceError(Exception):
    """Raised when AI extraction cannot complete."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ---------------------------------------------------------------------------
# Step 1 prompt — just read, don't structure
# ---------------------------------------------------------------------------

READ_PROMPT = """Read this receipt image and transcribe ALL text you can see, exactly as printed.

Include every line:
- TAX ID or VAT registration number
- Date and time
- Receipt or invoice number
- Every line item: code, name, quantity, and price
- Subtotal, VAT/tax, discount, total amount
- Payment method (cash, card, PromptPay, QR, etc.)

Important:
- Copy Thai text exactly as you see it, character by character
- Copy numbers exactly (do not round or change)
- If a field is not visible, skip it — do not guess

Output only the transcribed text. No analysis, no JSON, no explanation."""


# ---------------------------------------------------------------------------
# Step 2 — Python parser: extract fields from OCR text
# ---------------------------------------------------------------------------

# ── Date helpers ──────────────────────────────────────────────────────────────

_DATE_RE = re.compile(
    r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})\b"
)
_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b")


def _parse_date(text: str) -> date | None:
    """Find a date in text and convert Thai BE years to CE."""
    for m in _DATE_RE.finditer(text):
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            # 2-digit year: 69 → 2569 BE
            if y < 100:
                y += 2500
            # 4-digit BE year (> 2100): subtract 543
            if y > 2100:
                y -= 543
            # Sanity: reject obviously wrong dates
            if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
                return date(y, mo, d)
        except (ValueError, OverflowError):
            continue
    return None


def _parse_time(text: str) -> time | None:
    """Find the first HH:MM or HH:MM:SS in text."""
    m = _TIME_RE.search(text)
    if not m:
        return None
    try:
        h, mn, s = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
        if 0 <= h <= 23 and 0 <= mn <= 59 and 0 <= s <= 59:
            return time(h, mn, s)
    except ValueError:
        pass
    return None


# ── Money helpers ─────────────────────────────────────────────────────────────

_MONEY_RE = re.compile(r"(\d[\d,]*\.?\d*)")
_TOTAL_LINE_RE = re.compile(
    r"(?:total|รวม|ยอดรวม|ยอดชำระ|amount\s*due)[^\d]*(\d[\d,]*\.?\d*)",
    re.IGNORECASE,
)


def _to_decimal(s: str) -> Decimal | None:
    if not s:
        return None
    try:
        return Decimal(s.replace(",", ""))
    except InvalidOperation:
        return None


def _find_total(text: str) -> Decimal | None:
    """Find the final total amount. Prefer explicit 'total' lines."""
    m = _TOTAL_LINE_RE.search(text)
    if m:
        d = _to_decimal(m.group(1))
        if d and d > 0:
            return d
    # Fallback: find the largest monetary value on a line that looks like a total
    best: Decimal | None = None
    for line in text.splitlines():
        if re.search(r"total|รวม|ยอดรวม|ยอดชำระ", line, re.IGNORECASE):
            for num_m in _MONEY_RE.finditer(line):
                d = _to_decimal(num_m.group(1))
                if d and (best is None or d > best):
                    best = d
    return best


# ── TAX ID helper ─────────────────────────────────────────────────────────────

_TAX_ID_RE = re.compile(
    r"(?:tax\s*id|vat|เลขประจำตัวผู้เสียภาษี|เลขที่ผู้เสียภาษี)[^\d]*(\d[\d\-\s]{9,16}\d)",
    re.IGNORECASE,
)
_DIGITS13_RE = re.compile(r"\b(\d{13})\b")


def _find_tax_id(text: str) -> str | None:
    m = _TAX_ID_RE.search(text)
    if m:
        return re.sub(r"[\s\-]", "", m.group(1))
    # Fallback: look for any standalone 13-digit number
    m = _DIGITS13_RE.search(text)
    if m:
        return m.group(1)
    return None


# ── Receipt number helper ─────────────────────────────────────────────────────

_RECEIPT_NO_RE = re.compile(
    r"(?:receipt\s*no\.?|invoice\s*no\.?|เลขที่|no\.)[\s:]*([A-Z0-9][A-Z0-9/\-]{3,30})",
    re.IGNORECASE,
)


def _find_receipt_number(text: str) -> str | None:
    m = _RECEIPT_NO_RE.search(text)
    return m.group(1).strip() if m else None


# ── Shop name helper ──────────────────────────────────────────────────────────

def _find_paid_to(text: str) -> str | None:
    """Return the first non-empty, non-address line that looks like a shop name."""
    for line in text.splitlines():
        line = line.strip()
        # Skip obviously non-name lines
        if not line:
            continue
        if re.match(r"^\d", line):  # starts with digit — likely address or number
            continue
        if re.search(r"(?:tax|vat|date|time|receipt|total|subtotal|payment|cashier|table)", line, re.IGNORECASE):
            continue
        if len(line) < 3 or len(line) > 80:
            continue
        return line
    return None


# ── Payment method helper ─────────────────────────────────────────────────────

_PAYMENT_RE = re.compile(
    r"\b(cash|card|credit|debit|promptpay|prompt\s*pay|qr|โอนเงิน|เงินสด|บัตรเครดิต)\b",
    re.IGNORECASE,
)


def _find_payment_method(text: str) -> str | None:
    m = _PAYMENT_RE.search(text)
    return m.group(1).strip().title() if m else None


# ── Item parser ───────────────────────────────────────────────────────────────

_ITEM_LINE_RE = re.compile(
    r"^(\d+)\s+(.+?)\s+(\d[\d,]*\.\d{2})$"
)


def _parse_items(text: str) -> list[ExtractedReceiptItem]:
    """Extract line items from OCR text.

    Handles lines like:
      1  ซูชิกุ้ง  39.00
      2  (A21) ซูชิแซลมอน  38.00
    """
    items: list[ExtractedReceiptItem] = []
    for line in text.splitlines():
        line = line.strip()
        m = _ITEM_LINE_RE.match(line)
        if not m:
            continue
        qty_str, name_raw, price_str = m.group(1), m.group(2).strip(), m.group(3)
        # Skip summary lines
        if re.search(r"total|subtotal|vat|discount|รวม|ยอด|item", name_raw, re.IGNORECASE):
            continue
        # Skip quantity > 20 (likely address number or code, not qty)
        try:
            qty_val = int(qty_str)
            if qty_val > 20:
                continue
        except ValueError:
            continue
        # Skip if name is just digits or very short
        if re.match(r"^\d+$", name_raw) or len(name_raw) < 2:
            continue
        qty = _to_decimal(qty_str) or Decimal("1")
        price = _to_decimal(price_str) or Decimal("0")
        items.append(
            ExtractedReceiptItem(
                original_name=name_raw,
                name_en=None,
                name_th=name_raw if _has_thai(name_raw) else None,
                quantity=qty,
                total_price=price,
                discount_amount=Decimal("0"),
            )
        )
    return items


def _has_thai(text: str) -> bool:
    return bool(re.search(r"[\u0e00-\u0e7f]", text))


# ── Category guesser (keyword fallback) ───────────────────────────────────────

_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Food & Drink", [
        "sushi", "restaurant", "cafe", "coffee", "food", "drink", "bar",
        "grill", "kitchen", "bakery", "noodle", "ramen", "bbq", "steak",
        "seafood", "bistro", "shinkanzen", "the mall", "mcdonalds", "kfc",
        "subway", "starbucks", "pizza", "burger",
        "ร้านอาหาร", "อาหาร", "เครื่องดื่ม", "กาแฟ", "ชา", "ข้าว",
        "ก๋วยเตี๋ยว", "ซูชิ", "ปลา", "หมู", "ไก่", "กุ้ง", "ผัก",
    ]),
    ("Transport", [
        "taxi", "grab", "uber", "bus", "train", "bts", "mrt", "toll",
        "fuel", "petrol", "parking", "airport",
        "แท็กซี่", "รถ", "น้ำมัน", "ทางด่วน",
    ]),
    ("Shopping", [
        "mall", "shop", "store", "market", "supermarket", "lotus", "bigc",
        "tops", "central", "robinson",
        "ห้างสรรพสินค้า", "ซูเปอร์มาร์เก็ต",
    ]),
    ("Healthcare", [
        "hospital", "clinic", "pharmacy", "drug", "medicine", "dental",
        "โรงพยาบาล", "คลินิก", "ร้านยา",
    ]),
    ("Accommodation", [
        "hotel", "resort", "hostel", "inn", "motel",
        "โรงแรม", "รีสอร์ท",
    ]),
    ("Entertainment", [
        "cinema", "movie", "concert", "game", "sport", "gym", "fitness",
        "โรงหนัง", "กีฬา", "ฟิตเนส",
    ]),
    ("Utilities", [
        "electric", "water", "internet", "phone", "mobile", "dtac", "ais", "true",
        "ไฟฟ้า", "น้ำประปา", "อินเทอร์เน็ต",
    ]),
    ("Education", [
        "school", "university", "course", "tutor", "book",
        "โรงเรียน", "มหาวิทยาลัย",
    ]),
]


def _guess_category(text: str) -> str:
    """Return the best matching category name or 'Other'."""
    lower = text.lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw in lower:
                return category
    return "Other"


# ── Main OCR-text → ExtractedReceiptData ─────────────────────────────────────

def _parse_ocr_to_data(ocr_text: str) -> ExtractedReceiptData:
    """Convert raw OCR text into a validated ExtractedReceiptData object."""
    receipt_date = _parse_date(ocr_text)
    receipt_time = _parse_time(ocr_text)
    total = _find_total(ocr_text)
    tax_id = _find_tax_id(ocr_text)
    receipt_no = _find_receipt_number(ocr_text)
    paid_to = _find_paid_to(ocr_text)
    payment = _find_payment_method(ocr_text)
    items = _parse_items(ocr_text)
    category = _guess_category(ocr_text)

    # Detect language: if any Thai unicode block chars → "th"
    language = "th" if _has_thai(ocr_text) else "en"

    # total_amount is required — use 0 if we genuinely can't find it
    if total is None:
        total = Decimal("0")

    return ExtractedReceiptData(
        paid_to=paid_to,
        tax_id=tax_id,
        category_name=category,
        receipt_number=receipt_no,
        receipt_date=receipt_date,
        receipt_time=receipt_time,
        document_type=None,
        payment_method=payment,
        currency="THB",
        subtotal=None,
        tax_amount=None,
        discount_amount=None,
        total_amount=total,
        language_detected=language,
        ai_confidence=Decimal("0.75"),
        items=items,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_client() -> OpenAI:
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
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*([\s\S]*?)```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    return text


# ---------------------------------------------------------------------------
# Public extraction function
# ---------------------------------------------------------------------------


def extract_receipt_data(
    file_path: Path | str,
    mime_type: str,
) -> tuple[ExtractedReceiptData, str]:
    """Two-step receipt extraction.

    Step 1 — Vision call: AI reads and transcribes all text from the image.
    Step 2 — Python parsing: Our code structures the OCR text into typed fields.

    Returns (ExtractedReceiptData, ocr_text).
    The ocr_text is also passed back so receipt_service can apply extra fallbacks.
    """
    client = _build_client()

    if mime_type not in SUPPORTED_MIME_TYPES:
        raise GeminiServiceError(
            f"Unsupported receipt file type: {mime_type}", status_code=415
        )

    path = Path(file_path)
    if not path.is_file():
        raise GeminiServiceError("Receipt file not found", status_code=404)

    file_bytes = path.read_bytes()
    b64_image = base64.b64encode(file_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64_image}"

    # ── Step 1: Vision — AI reads the image ──────────────────────────────────
    try:
        response = client.chat.completions.create(
            model=settings.OPENROUTER_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": READ_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
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

    ocr_text = (
        response.choices[0].message.content if response.choices else None
    )
    if not ocr_text or not ocr_text.strip():
        raise GeminiServiceError("AI returned an empty response")

    # ── Step 2: Python parsing — structure the OCR text ──────────────────────
    try:
        extracted = _parse_ocr_to_data(ocr_text)
    except Exception as exc:
        raise GeminiServiceError("Failed to parse receipt text") from exc

    return extracted, ocr_text
