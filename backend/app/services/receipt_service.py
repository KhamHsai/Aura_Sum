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
    file_path = save_receipt_file(file_bytes, stored_filename, settings.UPLOAD_DIR)

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

def _find_category_by_name(db: Session, name: str | None) -> int | None:
    """Return the id of an active, non-deleted category whose name_en or name_th
    matches the given string (case-insensitive), or None if no match is found.
    Does not create categories automatically.
    """
    if not name or not name.strip():
        return None

    search = name.strip().lower()

    category = (
        db.query(Category)
        .filter(
            Category.is_active == True,
            Category.deleted_at.is_(None),
        )
        .all()
    )

    for cat in category:
        if cat.name_en.lower() == search or cat.name_th.lower() == search:
            return cat.id

    return None


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

    # 4. Call Gemini — GeminiServiceError is allowed to propagate unchanged.
    extracted = extract_receipt_data(file_path, receipt.mime_type)

    # 5. Simple category matching (case-insensitive, active only).
    expense_category_id = _find_category_by_name(db, None)  # no main category field in schema
    # Note: ExtractedReceiptData has no top-level category_name field.
    # Each item has category_name; the expense category remains None.

    # 6. Build the title (fallback chain: title → merchant_name → "Extracted Receipt").
    title = (
        extracted.title
        or extracted.merchant_name
        or "Extracted Receipt"
    )

    # 7. Determine receipt_date — use today if Gemini didn't return one.
    receipt_date = extracted.receipt_date or date.today()

    try:
        # 8. Create the Expense.
        expense = Expense(
            user_id=user_id,
            category_id=expense_category_id,  # None when no match
            title=title,
            merchant_name=extracted.merchant_name,
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
            is_confirmed=False,
        )
        db.add(expense)
        db.flush()  # get expense.id without committing

        # 9. Create ExpenseItems.
        created_items: list[ExpenseItem] = []
        for item_data in extracted.items:
            # Skip items with no usable name at all.
            if not item_data.original_name and not item_data.name_en and not item_data.name_th:
                continue

            item_category_id = _find_category_by_name(db, item_data.category_name)

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
        item_responses = [ExpenseItemResponse.model_validate(item) for item in created_items]
        return ExpenseResponse(
            id=expense.id,
            user_id=expense.user_id,
            category_id=expense.category_id,
            title=expense.title,
            merchant_name=expense.merchant_name,
            receipt_number=expense.receipt_number,
            receipt_date=expense.receipt_date,
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
