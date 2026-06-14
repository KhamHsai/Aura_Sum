from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.expense import ExpenseResponse
from app.schemas.receipt import ReceiptFileResponse
from app.services.gemini_service import GeminiServiceError
from app.services.receipt_service import (
    ReceiptServiceError,
    delete_user_receipt,
    extract_receipt_to_draft_expense,
    get_user_receipt_by_id,
    get_user_receipts,
    upload_receipt,
)

router = APIRouter(
    prefix="/api/receipts",
    tags=["Receipts"],
)


@router.post(
    "/upload",
    response_model=ReceiptFileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a receipt file",
)
async def upload_receipt_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReceiptFileResponse:
    """Upload a JPEG, PNG, WEBP, or PDF receipt (max 10 MB)."""
    try:
        file_bytes = await file.read()
    finally:
        await file.close()

    try:
        receipt_file = upload_receipt(
            db=db,
            user_id=current_user.id,
            original_filename=file.filename or "",
            content_type=file.content_type or "",
            file_bytes=file_bytes,
        )
    except ReceiptServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return receipt_file


@router.get(
    "",
    response_model=list[ReceiptFileResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Receipts",
)
def list_receipts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReceiptFileResponse]:
    """Return all non-deleted receipts for the authenticated user, newest first."""
    return get_user_receipts(db, current_user.id)


@router.get(
    "/{receipt_id}",
    response_model=ReceiptFileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Receipt Details",
)
def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReceiptFileResponse:
    """Return a single receipt owned by the authenticated user."""
    receipt = get_user_receipt_by_id(db, current_user.id, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt


@router.delete(
    "/{receipt_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Receipt",
)
def delete_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Soft-delete a receipt owned by the authenticated user."""
    deleted = delete_user_receipt(db, current_user.id, receipt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return {"message": "Receipt deleted successfully"}


@router.post(
    "/{receipt_id}/extract",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Extract Receipt Data",
)
def extract_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseResponse:
    """Extract data from a receipt with Gemini and create a draft expense."""
    try:
        return extract_receipt_to_draft_expense(db, current_user.id, receipt_id)
    except ReceiptServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except GeminiServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
