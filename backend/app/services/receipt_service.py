import re
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.expense import Expense
from app.models.expense_item import ExpenseItem
from app.models.receipt_file import ReceiptFile
from app.config import settings
from app.schemas.expense import ExpenseResponse
from app.schemas.expense_item import ExpenseItemResponse
from app.services.gemini_service import GeminiServiceError, extract_receipt_data
from app.utils.file_utils import (
    validate_receipt_file,
    generate_stored_filename,
    save_receipt_file,
    delete_saved_file,
)


class ReceiptServiceError(Exception):
    """Raised for receipt upload errors."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def upload_receipt(
    db: Session,
    user_id: int,
    original_filename: str,
    content_type: str,
    file_bytes: bytes,
) -> ReceiptFile:
    """
    Validate, save, and record an uploaded receipt file.

    Order of operations:
    1. Validate the file.
    2. Generate a unique stored filename.
    3. Save the file to disk.
    4. Insert a receipt_files database record.
    5. Clean up the physical file if the DB commit fails.
    """
    max_size_bytes = settings.MAX_RECEIPT_FILE_SIZE_MB * 1024 * 1024

    # Step 1 – validate
    try:
        validate_receipt_file(original_filename, content_type, file_bytes, max_size_bytes)
    except ValueError as exc:
        msg = str(exc)
        if "too large" in msg:
            raise ReceiptServiceError(msg, status_code=413)
        if "Unsupported" in msg:
            raise ReceiptServiceError(msg, status_code=415)
        raise ReceiptServiceError(msg, status_code=400)

    # Step 2 – unique stored filename
    stored_filename = generate_stored_filename(original_filename)

    # Step 3 – save to disk
    file_path = save_receipt_file(file_bytes, stored_filename, str(settings.upload_dir_absolute))

    # Steps 4-5 – DB record; clean up file on failure
    try:
        receipt_file = ReceiptFile(
            user_id=user_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            mime_type=content_type,
            file_size=len(file_bytes),
            upload_status="uploaded",
        )
        db.add(receipt_file)
        db.commit()
        db.refresh(receipt_file)
        return receipt_file
    except Exception:
        db.rollback()
        delete_saved_file(file_path)
        raise


# ── Receipt management ────────────────────────────────────────────────────────

def get_user_receipts(db: Session, user_id: int) -> list:
    """Return all non-deleted receipts for a user, newest first."""
    return (
        db.query(ReceiptFile)
        .filter(
            ReceiptFile.user_id == user_id,
            ReceiptFile.deleted_at.is_(None),
        )
        .order_by(ReceiptFile.uploaded_at.desc())
        .all()
    )


def get_user_receipt_by_id(
    db: Session, user_id: int, receipt_id: int
) -> ReceiptFile | None:
    """Return a receipt only when it belongs to the user and is not soft-deleted."""
    return (
        db.query(ReceiptFile)
        .filter(
            ReceiptFile.id == receipt_id,
            ReceiptFile.user_id == user_id,
            ReceiptFile.deleted_at.is_(None),
        )
        .first()
    )


def delete_user_receipt(db: Session, user_id: int, receipt_id: int) -> bool:
    """Soft-delete a receipt. Returns True on success, False when not found."""
    receipt = get_user_receipt_by_id(db, user_id, receipt_id)
    if receipt is None:
        return False
    try:
        receipt.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


# ── Extraction ────────────────────────────────────────────────────────────────

# Keywords used to guess category from merchant name or item names when the AI
# returns null or a wrong value.
_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Food & Drink", [
        "sushi", "restaurant", "cafe", "coffee", "pizza", "burger", "food", "drink",
        "bar", "grill", "kitchen", "bakery", "noodle", "ramen", "bbq", "steak",
        "seafood", "bistro", "eatery", "thai", "chinese", "japanese", "italian",
        "shinkanzen", "the mall", "mcdonalds", "kfc", "subway", "starbucks",
        # Thai keywords
        "ร้านอาหาร", "อาหาร", "เครื่องดื่ม", "กาแฟ", "ชา", "ข้าว", "ก๋วยเตี๋ยว",
        "ซูชิ", "ปลา", "หมู", "ไก่", "กุ้ง", "ผัก",
    ]),
    ("Transport", [
        "taxi", "grab", "uber", "bus", "train", "bts", "mrt", "toll", "fuel",
        "petrol", "gas", "parking", "car", "transport", "airport",
        "แท็กซี่", "รถ", "น้ำมัน", "ทางด่วน", "บีทีเอส", "รถไฟ",
    ]),
    ("Shopping", [
        "mall", "shop", "store", "market", "supermarket", "lotus", "bigc", "tops",
        "central", "robinson", "เซ็นทรัล", "ห้างสรรพสินค้า", "ซูเปอร์มาร์เก็ต",
    ]),
    ("Healthcare", [
        "hospital", "clinic", "pharmacy", "drug", "medicine", "dental", "doctor",
        "โรงพยาบาล", "คลินิก", "ร้านยา", "ยา",
    ]),
    ("Accommodation", [
        "hotel", "resort", "hostel", "inn", "motel", "airbnb",
        "โรงแรม", "รีสอร์ท",
    ]),
    ("Entertainment", [
        "cinema", "movie", "concert", "game", "sport", "gym", "fitness",
        "โรงหนัง", "ภาพยนตร์", "กีฬา", "ฟิตเนส",
    ]),
    ("Utilities", [
        "electric", "water", "internet", "phone", "mobile", "dtac", "ais", "true",
        "ไฟฟ้า", "น้ำประปา", "อินเทอร์เน็ต", "โทรศัพท์",
    ]),
    ("Education", [
        "school", "university", "course", "tutor", "book", "library",
        "โรงเรียน", "มหาวิทยาลัย", "หนังสือ",
    ]),
]

_THAI_BE_DATE_RE = re.compile(
    r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})\b"
)


def _guess_category_from_text(text: str) -> str | None:
    """Return a category name by keyword-matching against merchant/item text."""
    if not text:
        return None
    lower = text.lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw in lower:
                return category
    return None


def _parse_thai_be_date(raw_date_text: str | None) -> date | None:
    """Try to extract and convert a Thai Buddhist Era date string to a CE date.

    Handles formats like:
      - "12/06/69"  → 2026-06-12  (2-digit year: treat as BE 256x)
      - "12/06/2569" → 2026-06-12 (4-digit BE year)
      - "12/06/2026" → 2026-06-12 (already CE — detect by year > 2100 means BE)
    Returns None when parsing fails.
    """
    if not raw_date_text:
        return None
    m = _THAI_BE_DATE_RE.search(raw_date_text)
    if not m:
        return None
    try:
        day, month, year_str = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # 2-digit year: 69 → 2569 BE → 2026 CE
        if year_str < 100:
            year_str += 2500  # treat as BE
        # 4-digit year > 2100 is definitely BE
        if year_str > 2100:
            year_str -= 543
        return date(year_str, month, day)
    except (ValueError, OverflowError):
        return None


def _find_or_create_category(db: Session, name: str | None) -> int | None:
    """Return the id of a matching category, creating it if needed.

    Matching (case-insensitive):
    1. Exact match on name_en or name_th.
    2. Contains match (handles "food" → "Food & Drink").
    3. No match → create new category with that name.
    Returns None only when name is blank.
    """
    if not name or not name.strip():
        return None

    search = name.strip().lower()

    categories = (
        db.query(Category)
        .filter(Category.is_active == True, Category.deleted_at.is_(None))
        .all()
    )

    # Exact match
    for cat in categories:
        if (cat.name_en or "").lower() == search or (cat.name_th or "").lower() == search:
            return cat.id

    # Partial / contains match
    for cat in categories:
        name_en = (cat.name_en or "").lower()
        name_th = (cat.name_th or "").lower()
        if search in name_en or name_en in search or search in name_th or name_th in search:
            return cat.id

    # Create new category
    slug = re.sub(r'[^a-z0-9]+', '_', search).strip('_')[:50] or 'category'
    code = slug
    counter = 1
    while db.query(Category).filter(Category.code == code).first():
        code = f"{slug}_{counter}"
        counter += 1

    new_cat = Category(code=code, name_en=name.strip(), name_th=name.strip(), is_active=True)
    db.add(new_cat)
    db.flush()
    return new_cat.id


def extract_receipt_to_draft_expense(
    db: Session,
    user_id: int,
    receipt_id: int,
) -> ExpenseResponse:
    """Extract a receipt with Gemini and create a draft Expense + ExpenseItems.

    Steps:
    1. Find the receipt (must be owned, active, and unlinked).
    2. Confirm the physical file exists.
    3. Call Gemini.
    4. Match categories by name.
    5. Create the Expense.
    6. Create ExpenseItems.
    7. Link the receipt to the expense.
    8. Commit once.
    9. Return ExpenseResponse with nested items.

    Raises ReceiptServiceError for 404/409 business errors.
    Re-raises GeminiServiceError unchanged so the route can forward its status code.
    Rolls back all DB changes on any failure.
    """
    # 1. Find the receipt — ownership + soft-delete check in one query.
    receipt = (
        db.query(ReceiptFile)
        .filter(
            ReceiptFile.id == receipt_id,
            ReceiptFile.user_id == user_id,
            ReceiptFile.deleted_at.is_(None),
        )
        .first()
    )
    if receipt is None:
        raise ReceiptServiceError("Receipt not found", status_code=404)

    # 2. Already linked to an expense?
    if receipt.expense_id is not None:
        raise ReceiptServiceError(
            "Receipt is already linked to an expense", status_code=409
        )

    # 3. Confirm the physical file is present.
    file_path = Path(receipt.file_path)
    if not file_path.is_file():
        raise ReceiptServiceError("Receipt file not found", status_code=404)

    # 4. Call AI — GeminiServiceError is allowed to propagate unchanged.
    extracted, ai_raw_text = extract_receipt_data(file_path, receipt.mime_type)

    # 4a. Fix date: if AI returned null for receipt_date, check receipt_date_raw
    #     and also scan the full raw response text for a Thai BE date pattern.
    receipt_date_resolved: date | None = extracted.receipt_date
    if receipt_date_resolved is None:
        # The AI may have put the raw date string in receipt_date_raw — it's in the
        # raw JSON text even though it's not in our schema. Scan raw text for it.
        receipt_date_resolved = _parse_thai_be_date(ai_raw_text)

    # 4b. Fix category: if AI returned null or generic "Other", use keyword
    #     fallback based on paid_to and first few item names.
    category_text = extracted.category_name
    if not category_text or category_text.strip().lower() == "other":
        search_corpus = " ".join(filter(None, [
            extracted.paid_to,
        ] + [
            (item.original_name or item.name_th or item.name_en or "")
            for item in extracted.items[:5]
        ]))
        # Also scan the full raw response for merchant/restaurant clues
        search_corpus += " " + ai_raw_text[:500]
        guessed = _guess_category_from_text(search_corpus)
        if guessed:
            category_text = guessed

    # 5. Category matching — use resolved category text.
    expense_category_id = _find_or_create_category(db, category_text)

    # 6. Build paid_to: use explicit paid_to only.
    paid_to = extracted.paid_to

    # 7. Determine receipt_date — use extracted or parsed date, not today.
    receipt_date = receipt_date_resolved or date.today()

    try:
        # 8. Create the Expense.
        expense = Expense(
            user_id=user_id,
            category_id=expense_category_id,
            paid_to=paid_to,
            tax_id=extracted.tax_id,
            receipt_number=extracted.receipt_number,
            receipt_date=receipt_date,
            receipt_time=extracted.receipt_time,
            document_type=extracted.document_type,
            payment_method=extracted.payment_method,
            currency=extracted.currency or "THB",
            subtotal=extracted.subtotal,
            tax_amount=extracted.tax_amount,
            discount_amount=extracted.discount_amount,
            total_amount=extracted.total_amount,
            language_detected=extracted.language_detected,
            ai_confidence=extracted.ai_confidence,
            ai_raw_response=extracted.model_dump(mode="json"),
            input_method="ai",
            ai_status="completed",
            is_confirmed=True,
        )
        db.add(expense)
        db.flush()  # get expense.id without committing

        # 9. Create ExpenseItems.
        created_items: list[ExpenseItem] = []
        for item_data in extracted.items:
            # Skip items with no usable name at all.
            if not item_data.original_name and not item_data.name_en and not item_data.name_th:
                continue

            item_category_id = _find_or_create_category(db, item_data.category_name)

            item = ExpenseItem(
                expense_id=expense.id,
                category_id=item_category_id,
                original_name=item_data.original_name or item_data.name_en or item_data.name_th,
                name_en=item_data.name_en,
                name_th=item_data.name_th,
                quantity=item_data.quantity or 1,
                unit=item_data.unit,
                unit_price=item_data.unit_price,
                discount_amount=item_data.discount_amount or 0,
                total_price=item_data.total_price or 0,
            )
            db.add(item)
            created_items.append(item)

        db.flush()  # get item IDs

        # 10. Link the receipt.
        receipt.expense_id = expense.id

        # 11. Commit once — all three changes succeed together or none do.
        db.commit()

        # 12. Refresh to load server-generated timestamps.
        db.refresh(expense)
        for item in created_items:
            db.refresh(item)

        # 13. Build the response while the session is still open.
        response_category_name: str | None = None
        if expense.category_id:
            cat = db.query(Category).filter(Category.id == expense.category_id).first()
            if cat:
                response_category_name = cat.name_en or cat.name_th
        if not response_category_name:
            response_category_name = category_text

        item_responses = [ExpenseItemResponse.model_validate(item) for item in created_items]
        return ExpenseResponse(
            id=expense.id,
            user_id=expense.user_id,
            category_id=expense.category_id,
            category_name=response_category_name,
            paid_to=expense.paid_to,
            tax_id=expense.tax_id,
            receipt_number=expense.receipt_number,
            receipt_date=expense.receipt_date,
            receipt_time=expense.receipt_time,
            payment_method=expense.payment_method,
            currency=expense.currency,
            subtotal=expense.subtotal,
            tax_amount=expense.tax_amount,
            discount_amount=expense.discount_amount,
            total_amount=expense.total_amount,
            notes=None,
            is_confirmed=expense.is_confirmed,
            created_at=expense.created_at,
            updated_at=expense.updated_at,
            items=item_responses,
        )

    except (ReceiptServiceError, GeminiServiceError):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
