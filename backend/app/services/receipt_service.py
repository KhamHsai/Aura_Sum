from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.receipt_file import ReceiptFile
from app.config import settings
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
